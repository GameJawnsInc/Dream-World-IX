# W6b-3 (iii) — THE U1 SECOND-ARRAY CAST. ef038 `Shiva`, bench row 200, both halves of column 640

> ★★★ **STATE — THE ARC IS CLOSED AT THE MECHANISM (§12). The second array is a per-slot texel
> DISPLACEMENT baked into the primitive stream: pair position 0 moves u, position 1 moves v, +0x80 =
> +128 texels each — measured at 0.97 on ef038 by the s77 UVR read, all four (A,B) cells on
> independent populations, critic ok=true ZERO gaps.** The 0.68 screen labelling is RETIRED for a
> measurement; the pitch/v axis is RESOLVED (no cast 3 needed); cast 1's null is fully mechanical;
> the Option-3 gate is MET on ef038. The road: cast 1 (§9) VISIBLE_UNBANDED → s76 + the control cast
> (§9.3): G1 THE PAGE-SPAN GATE, blit-wipe refuted → cast 2 (§10-§11): orientation resolved 0.84 →
> s77 (§12): the mechanism. BINDING LIMIT: one container — a second container's log-only cast makes
> it a law. Install stock except the s76+s77 engine instruments; rows 192–204 stay. **Owner
> decisions: the §12 stale-text ledger (the U_DISPLACEMENT_CAVEAT triple is now outdated), the
> Option-3 follow-on, R_UOFF's status line, a second-container generalisation cast.**
> Records: `…\u1-second-array\{castread\REPORT-U1, s76-read\REPORT-S76, cast2-read\REPORT-U1-CAST2,
> s77-read\REPORT-S77-READ}.md`.
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

1. ~~**⚠ ENGINE (owner GO/NO-GO — DLL rebuild): log the `DR_MOVE`/`MoveImage` payload rects**~~
   **→ ★ DONE — owner said GO; s76 BUILT + DEPLOYED 2026-07-30** (`memoria-patches/
   s76-sfx-state-payload.patch`, one file, +67/−6, additive-only on the CapturePrims gating; both
   arches sha `b6ce810f…`; pre-build backup `20260730-222511`; 0 committed parsers break — the one
   break was the SCRATCH `a22_drawproof.py` `endswith` idiom, which would have failed SILENTLY TO
   ZERO on the next capture and is fixed in place; full record in the README row). `DR_TPAGE` rows
   now carry `tpage,tx,ty,abr,tp,len` (the marked page (640,256) = `tx=10,ty=1`) and `DR_MOVE` rows
   carry their rects — **a block of `SS` rather than `MV` packets would REFUTE the blit mechanism,
   not confirm it**. RELAUNCH required (DLL change), then the §9.2 control cast.
2. **Dump the emulated VRAM page at (640,256) at cast time** and diff against the two marked cells —
   separates a wrong cells→VRAM mapping from a runtime overwrite from a cached decode.
3. **A STOCK reference cast of ef038** (probe already reverted; recast + capture) — the only thing that
   ever makes the A=0x0000 control family scoreable on its own pixels.
4. **Only then** the §6.2 fallback vehicles (ef407 first) — every one inherits the same unproven
   cells→VRAM→sampler link this cast just exposed.
5. **Do NOT bundle the §4.4 second leg** (flip A, watch blend state). One change per in-game test; this
   cast has not earned that step.

### 9.2 The s76 control cast — the next in-game step (LOG-ONLY, no video needed)

**RELAUNCH FF9 first** (a DLL rebuild is a relaunch case; the game was closed for the build, so the
next launch picks s76 up). The install is stock — the probe is NOT deployed, on purpose: the control
cast asks what stock ef038 does to VRAM, with nothing of ours in the way.

1. Warp `30301` → STEINIV → `Rune` → **"Stock Shiva"** (row 200), fresh encounter, FIRST action.
2. **Archive `sfxmeshprobe.log` to `capture-logs\` immediately** — this read is entirely in the log.
3. THE READ: the `STATE` rows now carry payloads. Under the blit hypothesis, `MV`-class `DR_MOVE`
   rows appear in the early block (effect frames ~86–138) with **destination rects intersecting the
   marked page — `tx=10, ty=1` in `DR_TPAGE` terms, VRAM (640,256)–(703,383)** — before any scenery
   draws. Moves that never touch that rect, **or a block of `SS` rather than `MV` packets, REFUTE
   the blit mechanism** and the search moves to the cells→VRAM-mapping / cached-decode branches
   (next steps 2–3 above). Either way the twin-pair co-draw question gets its answer free from the
   `DR_TPAGE` code words.
4. Only as a separate second test (one change per cast): redeploy the probe
   (`py u1_cell_probe.py --deploy`, no relaunch) and recast — the marked cast, now fully
   instrumented.

**Resting state:** ef038 override DELETED (= stock, verified), `ef211` untouched, rows 192–204 on the
bench, video + frames + all analysis under `…\repaint-w6b\u1-second-array\`, the `[SfxProbe]` log
archived in `capture-logs\`. **No constant moved; `ORDER_UNMEASURED` ships exactly as it was.**

### 9.3 ★★ THE s76 CONTROL CAST — READ AND ADJUDICATED. The mechanism is an INSTRUMENT DEFECT, and the census was the wrong instrument

Stock ef038, probe NOT deployed, log-only, after the s76 relaunch. Log archived at
`capture-logs\sfxmeshprobe.s76-control-cast.log` (24 MB, 485,919 rows). Read by a verifier pass and an
explainer pass, then adjudicated — the load-bearing numbers re-run from the saved scripts and, with two recorded
exceptions (the gate-ladder chain and the 76/76 repair claim were re-run from the explainer's own
scripts, not independently re-implemented), re-derived by an independent third parser; the critic's
full findings ride the report as an addendum. Scripts + JSON: `…\u1-second-array\s76-read\`
(`verify\`, `explain\`, `adjudicate\`). **No constant moved. Nothing written to the install, the repo,
or the Memoria clone.**

**THE THREE CENSUS FACTS.**

* **`DR_MOVE`: 641 rows on ef038, every one `MV`** — real VRAM blits, no framebuffer grabs. `path`
  re-derived from `SFXRender.cs:464` rather than trusting the logged token: **0/641** disagreements.
  The `SpecialEffect.Slow` `ry` adjustment (`:466-467`) is doubly inapplicable — it lives inside the SS
  branch, and `Slow = 126 ≠ 38`. The same 641 appear in the U1 cast: **the move stream is invariant
  between the marked and stock casts.**
* **The traffic is THREE scrolling-texture animations, not a wipe.** Block 1 (f86-138, **105** moves)
  rolls a strip horizontally at −2 px/frame on pages tx=8/9. Block 2 (f237-380, **536** moves) is two
  vertical barrel rolls: column 640 at +1 row/frame (**284** moves; lower cell = read-only MASTER →
  upper cell = write-only COPY) and column 704 at +2 (**252** moves, mirror direction), phase-locked at
  f254. **The parent's 357 and 284 were both wrong** — 357 = 105 + 252, two different blocks on two
  different page pairs; its exemplar dest ranges `(512,514)`/`(512,536)` do not occur at all.
* **`DR_TPAGE` never names tx=10 — anywhere.** Whole-log histogram over all 41,607 rows, all effects:
  `tx ∈ {0, 6, 7, 13}`. The parent's five ef038 classes reproduce to the row (bitfields re-derived from
  the raw word, 0 mismatches). Counts EXACT.

**⚠ THE HEADLINE INFERENCE IS REFUTED — and by one bit, not by attribution.** `SFXKey.GetCurrentABRTex`
(`SFXKey.cs:19-30`) is the ONLY consumer of the `DR_TPAGE` state, and a tree-wide grep gives it exactly
ONE call site: `SFXRender.cs:400`, the `SPRT` path — which **unconditionally** ORs `FILTER_BILINEAR`.
The six textured-polygon paths (`:342, 349, 356, 364, 372, 380`) call
`GetABRTex(code, clut, tag->tpage)` — the primitive's OWN page word — and never touch `currentTexPage`.
The probe already logs that key (`keyHex = SFXMeshBase._key`). So **a textured MESH key with zero
FILTER bits provably did not come from the `DR_TPAGE` channel.** Partitioning ef038's 9,200 MESH rows
on that bit, with no residue:

| channel | meshes | pages |
|---|---|---|
| SPRT (provably `DR_TPAGE` state) | 3,914 | tx=6, tx=7 |
| POLYGON (provably own `tag->tpage`) | 4,437 | tx=3, 4, 5, 7, **8**, **10** |
| untextured (`GetCurrentABR`) | 849 | tx=0 |

**`SPRT_pages == the census's textured pages` → `true`.** Not inference — set equality. **The
`DR_TPAGE` census IS the SPRITE census**, and must be renamed as such wherever §9 or any W6b-2 text
quotes it; reading it as the effect's page ledger is what produced the relocation hypothesis. The
verifier's paradox (pages selected ∩ pages moved = ∅) dissolves: `DR_MOVE` writes tx=8 and tx=10, which
are exactly the two polygon-channel pages carrying animation, and the per-frame `ClearKey`
(`PSXTextureMgr.cs:243`) is paid for readers that genuinely exist. tx=9/tx=11 have no key because an
8bpp page is two columns wide and they are the high halves of tx=8/tx=10.

**★ THE MARKED PAGE DREW. `tx=10, ty=1, 8bpp`, CLUTs `0x3DC0` (573 meshes, 112,354 tris, f214-361) and
`0x3D40` (190 meshes, 24,902 tris, f214-278)** — 763 meshes in the stock cast, **661 in the marked U1
cast** — at the bound page, the bound depth, and *exactly* the two CLUTs the 27 so-records declare.
**BINDING-IS-NOT-A-DRAW is not the explanation, and the vehicle was never the problem.**

**★ THE ACTUAL DEFECT — G1, THE PAGE-SPAN GATE.** `GetTexture` builds every page as **256×256 texels**
(`PSXTextureMgr.cs:179`), and `CreateBufferColor32` steps `w>>2 / w>>1 / w` halfwords per row at
4/8/15 bpp from base `TX<<6`, `TY<<8` (`PSXTexture.cs:44-45, :51/:71/:91`). So **tpage
`tx=10,ty=1,tp=1` = VRAM x 640..767, y 256..511 = ALL FOUR declared cells** — (640,256), (640,384),
(704,256), (704,384), each a real 32 KB id-0 rect (payload offsets `0x146c…0x2146c`, `0x8000` apart).
**U1 marked TWO.** The MESH key names the page; only `u,v` choose the cell. A reader at `u ≥ 128`
samples column 704 — uploaded, blitted 252×/cast, and unmarked, hence indistinguishable from "not
sampled". Column 704 has no direct binder anywhere in ef038, so the only page word in the whole cast
that can address that 32 KB rect is tx=10 with `u ≥ 128`. Something reads it.

**THE BLIT WIPE — REFUTED AS STATED, and insufficient in any form.** Block 1 tops out at **x=639** on
both source and destination, one halfword short of 640; §9.2's own falsification criterion is met.
Block 2 *does* overwrite the entire upper marked cell on 143 consecutive frames from f237 — a real
confound the parent under-read, and one that would have collapsed the 12-THIN/4-FAT discriminant for
the whole back half of the effect — **but the marked page is sampled on f214-236, before the first
blit**: 164 meshes / 31,330 tris (stock), **134 meshes / 24,917 tris in the marked cast**. Substitution
of one mark for the other cannot produce ZERO. The tx=10 keys carry no FILTER bit — point sampling —
so nothing was blurred away either.

**THE CORRECTED VEHICLE CRITERION.** Old: *P=1, 8bpp, A=0x0080, forced part, no wrap.* Add:

* **G1 — page span.** `span_cols = {4bpp:1, 8bpp:2, 15bpp:4}` columns of 64 halfwords from `tx*64`.
  Passes iff **exactly one** column in the span is a declared rect — **or** the instrument marks
  **every** declared column in the span.
* **G2 — cell completeness.** Both 128-row cells of every such column are declared (U1 satisfied this
  for 640).

Pure container arithmetic — no cast, no engine. **ALL SIX §6.2 FALLBACKS FAIL G1**: ef038 `0x29dbc`,
ef407 `0x2a8c8`, ef498 `0x57620`, ef179 `0xa8ce8`/`0xa6a08`/`0xa4728`, ef381 `0x80820` — every one 8bpp
with a declared second column. And the list was not unlucky, it was **doomed by construction**: over
649 binding slots, 8bpp = 393 → `+A=0x80+P=1` = **76** → **`+G1` = 0**, because **364 of 393** 8bpp
bindings span two declared columns. The sketch required 8bpp (so OFFSET==SELECT), and 8bpp is exactly
the depth at which a page covers two columns.

**★ THE REPAIR — and it does not need a new vehicle.** Mark **all four cells of the page** with four
distinct gratings. **All 76** candidates pass, ef038 included. Same one cast, four marks instead of
two, and it upgrades the read from a 2-way to a **4-way** discriminator — resolving A (the v axis) and
B (the u axis) together. ef038 stays cheapest: bench row 200, no `Actions.csv` row, no relaunch.

**CHANNEL P — at the altitude the evidence supports.** P is **silent on ef038 and on ef211** (0 op-22
`Hi_RegisterTexEffModel` const-folded hits each, of 233 across 77 containers — figures CARRIED from
the prior round's `texel-w6b\w6b2	page_sweep.json`, critic-confirmed against that artifact but not
re-derived this round), so the intended
cross-check **cannot be run**. P and G are near-disjoint by construction — 77 P-containers vs 80
G-containers, overlap 13; ef038 and ef211 are both G-only — which is why P was DISCLOSE-only. They are
not rivals for the sampled-page question either: op-22 registers a *model's* page word, the same class
`tag->tpage` carries, so **P and G both speak for the POLYGON channel while the census speaks for the
SPRITE channel**. What can be said, and only this: on the **one** container where a runtime
sampled-page census now exists, all **8** of ef038's declared `(tx,ty,tp,clut)` signatures are real
draws at the declared page, depth and CLUT — **BINDING-IS-A-DRAW held 8/8**, an observation on one
container, not a corpus law. **"P DISCLOSES vs G LICENSES" survives unchanged; no posture change is
recommended, and any would need a second container. Owner's call, flagged not made.**

**HONEST LIMITS — what one stock cast cannot establish.**

1. **Which of the four cells was sampled.** The MESH key names page + depth + CLUT. It carries no
   `u,v`. Everything about *which cell* — the whole G1 story included — is inference from geometry,
   not measurement.
2. **H_U is a HYPOTHESIS, labelled as such.** That halfword B is a per-slot U displacement **in
   texels** is consistent (224/224 non-zero-B slots keep `u` inside the page; at 8bpp `B=128` lands
   exactly on the second column in 153/153, a declared rect in 150/153) and scores both in-game results
   (ef211's dome A=0,**B=0** → marks SEEN; ef038's disc A=128,**B=128** → marks UNSEEN). It is **not
   proven.** Contrary datum, stated: ef038's **7 A=0/B=0 control readers** (clut `0x3D40`, 161 meshes
   in the marked cast) should still have shown their marks — unless the operator scored that family's
   HOLE-class marks as blank, which §5 warns about in writing. **Re-opening R_UOFF in
   `second-array-lead\REPORT.md` §3 is an owner call** (its closure rests on "both u-shift conventions
   move slots OFF declared columns", which is false under the texel convention).
3. **Neither log proves the U1 override was resident during the marked cast.** A zero-writing probe is
   invisible to row counts by design; the two casts differ ~7-13 % in mesh counts with identical frame
   ranges (48..391). Ordinary variance, but not residency proof — closable with a one-byte non-zero
   canary in an unbound corner of the rect.
4. **Not re-derived:** the CLUT strips (`0x3D40` → VRAM (0,245), `0x3DC0` → (0,247)) are not among
   ef038's 12 declared rects; whatever uploads them was not traced, and the probe's entry-0 colour
   derivation depends on it.
5. **Two labelling defects in `explain\mesh.keys.json`** (headline unaffected, recorded so no one
   re-quotes them): its `tris` column is a `(tx,ty,tp)` PAGE aggregate printed in a per-key row (true
   per-key for the marked page: `0x3DC0` = **112,354**, not 137,256; `0x3D40` = **24,902**), and its
   "18 distinct keys" is a `(tx,ty,tp,clut)` collapse of **20** real keys — discarding exactly the
   FILTER bit that settles the round.

**NEXT STEP — one, and it is cheap.** Re-cast U1 on ef038 with **all four cells of page tx=10 marked**
— `(640,256) (640,384) (704,256) (704,384)`, four distinct gratings. Same vehicle, same protocol, no
relaunch, no engine change, no constant moved. Bracket it with the **MESH-key preflight** (free, needs
no new patch): one stock log-only cast, decode `MESH keyHex` bits 16-22 + 0-14, require the candidate's
`(tx,ty,tp,clut)` to appear — strictly stronger than the `DR_TPAGE` census, and it would have caught
this round before a container was written. **The proposed s77 `tag->tpage` probe is UNNECESSARY** — the
MESH key already gives the page. If H_U is ever to be settled from a log rather than a screen, the
thing to log is `tag->u0..u3 / v0..v3` on `SFXRender.cs:342-380`.

**Resting state:** unchanged from §9.2 — ef038 override DELETED (stock), `ef211` untouched, rows
192-204 on the bench. **No constant moved; `ORDER_UNMEASURED` ships exactly as it was.**

## 10. ★ CAST 2 — THE G1 REPAIR, STAGED. Four marks, two axes, one cast, no new vehicle

§9.3's "NEXT STEP — one, and it is cheap" is built and byte-proven, and it is staged only: **nothing is
deployed, the install is still stock** (`FF9CustomMap\FF9_Data\SpecialEffects\` holds exactly `ef211`,
530,432 B; no `ef038`), the repo is clean, and **no constant moved — `ORDER_UNMEASURED` ships exactly as
it was.** Everything below is derived at the machine with a citation; nothing is restated from memory.

**Staged sha `424761cd4a1e77620472e9ca70107322f402f2cf037c5cb7fc46e0bdec8da46e`, 555,008 B.**

### 10.1 The four marks, and why each is what it is

Cast 1 marked two of the four cells the page spans. Cast 2 marks all four, and spends the extra pair on a
SECOND axis rather than on more of the same one:

| cell | (A?, B?) | mark | duty | what a surface showing it says |
|---|---|---|---|---|
| `cell.s0.x640_y256` @`0x1946c` | (no, no) — **the control cell** | **COARSE VERTICAL**, 4 × 12 texels | 48/128 | neither halfword moves the sample |
| `cell.s0.x640_y384` @`0x1d46c` | (yes, no) | **FINE VERTICAL**, 12 × 4 | 48/128 | A moves it, B does not |
| `cell.s0.x704_y256` @`0x2146c` | (no, yes) | **COARSE HORIZONTAL**, 4 × 12 | 48/128 | B moves it (H_U), A does not |
| `cell.s0.x704_y384` @`0x2546c` | (yes, yes) | **FINE HORIZONTAL**, 12 × 4 | 48/128 | both are applied |

**ORIENTATION answers B and PITCH answers A, independently.** Duty is EXACTLY equal on all four — 37.5 %
— so neither axis has a brightness covariate and §5's DO-NOT-COUNT clause is strictly stronger than in
cast 1 (which ran 37.5 % against 25 %). COUNT 3:1, THICKNESS 1:3, and all six pairs are checked distinct
by code.

**Orientation carries the COLUMN axis because of the barrel roll, not in spite of it.** A vertical roll
copies whole rows, so it translates a horizontal grating — same pitch, moving phase, it CRAWLS — and
leaves a full-height vertical stripe PIXEL-IDENTICAL. So a column's orientation is on screen in every
frame and the roll cannot touch it, while a COPY cell's pitch becomes its master's at the roll onset.
Master and copy of a column must therefore share an axis; the probe refuses loudly if they ever do not.
**Column 704 gets the roll-visible HORIZONTAL orientation on three measured grounds**: it is where the
answer class lands if H_U holds, it rolls at +2 rows/frame against 640's +1, and its pre-roll window is
the longer one (f214..253 against f214..236). Column 640 gets VERTICAL, which leaves the control a
stable, never-scrolling grating whose pitch flips ONCE, at exactly f237 — a temporal signature that the
marked page is what is on screen.

**The pitch pair is chosen against a measured blur curve, not taste.** At the derived on-screen scale the
FINE class's near-black lift over stock is 33.8 / 24.0 / 12.9 / **0.65** points at σ = 0 / 1.5 / 3 / 4
screen px, while COARSE holds 35.7 / 32.4 / 28.0 / 25.0 and is still at 19.6 by σ = 6. Of every
equal-duty candidate pair, 12 × 4 against 4 × 12 keeps the largest separation at every sigma while
keeping four features rather than three. (Recorded disagreement: §9's report gives 3.93 % for the fine
mark at σ 1.5; that pass blurred the texture-space decode, roughly 3× harsher than screen px at this
scale. `cast2\build\blurprice.derivation.json`.)

**On-screen scale, from cast 1's own disc.** The disc `0x29dbc` samples 15,053 distinct texels and cast 1
measured its mask at ~147,000 px → 3.12 px per texel. A FINE feature is ~12.5 px on a ~33 px period; a
COARSE one ~37.5 px on a ~100 px period — both inside the 8–130 px band cast 1's sweep could resolve.

**Nothing is starved**, measured over all 27 readers: the worst-case fraction of a reader's faces
crossing a feature is 89.5 % / 97.2 % / 92.1 % / 97.2 % on the four cells.

⚠ **"VERTICAL" AND "HORIZONTAL" ARE TEXTURE-SPACE WORDS.** Each surface's UV mapping decides where they
land on screen, and on the orb they land nearly horizontal in both classes. What is projection-
independent — and is the actual claim — is that the two orientation classes differ by NINETY DEGREES ON
THE SAME SURFACE under any camera. Score against the §10.5 panels, never against the words.

### 10.2 The control, rebuilt — and cast 1's contradiction addressed

§9.3's honest limit 2 recorded a contrary datum: the 7 A=0/B=0 controls should have shown their marks and
did not, on an instrument that moved a 28.8 %-transparent baseline by ~1.9× against a stock reference
this arc has never captured. Cast 2 does not argue with that; it re-instruments it.

* **A threshold-free statistic with a stock floor of ZERO.** Under `0x3d40` the stock control cell has **0
  of 128 fully-transparent COLUMNS** and 4 fully-transparent ROWS — which is why the control's mark is
  VERTICAL and not horizontal. Marked, it has **48**. Secondary: opacity 71.2 % → 45.2 %, near-black area
  fraction 47.41 % → 63.81 %.
* **The COARSE class for the control**, because a 12-texel feature is ~37.5 screen px and survives the
  blur that erases a 4-texel one (§10.1).
* **A BRIGHT-FAMILY COLUMN CONTROL, which cast 1 did not have at all.** The column-640 census splits three
  ways once B is read: **(A,B) = (0,0) × 7, (0x80,0) × 1, (0x80,0x80) × 19**. That single (0x80, 0x00)
  slot is the wrap reader `0x79168`, on the OPAQUE `0x3dc0` palette: B cannot move it, so it must show a
  VERTICAL grating on the answer family's own palette in every frame. Score its orientation only — its v
  runs to 255, so its pitch is mixed by construction.
* **From f237 the control cell shows the master's FINE vertical stripes** — still VERTICAL, and the pitch
  change AT f237 is itself evidence the marked page is being sampled.

### 10.3 The residency canary — §9.3's honest limit 3, closed

One non-zero block per cell: **ink index 247 (`0xf7`)**, derived as the brightest index OPAQUE under BOTH
of the column's CLUTs — rgba(164,172,172) luma 169 under `0x3dc0`, rgba(156,172,172) luma 167 under
`0x3d40`. ~144 texels per cell, at a per-cell corner, **shaped to fit between that cell's own stripes** (a
coarse cell leaves 20-texel gaps → 12 × 12; a fine one leaves 7 → a 7 × 21 bar), inside the sampled row
span, and provably disjoint from every stripe. It moves a BRIGHT-tail statistic, orthogonal to the
near-black statistic the marks move. **It is not part of the read**, and the emitted protocol says so in
capitals — but a bright patch anywhere on an ef038 scenery surface proves the override was live in the
process, which no row count can.

### 10.4 The 4-way outcome, and what each branch is worth

| (A?, B?) | cell | clean window f214..236 | after the roll |
|---|---|---|---|
| (no, no) | (640,256) | COARSE VERTICAL | FINE VERTICAL from f237, static |
| (yes, no) | (640,384) | FINE VERTICAL | unchanged — MASTER |
| (no, yes) | (704,256) | COARSE HORIZONTAL | unchanged — MASTER, STATIC |
| (yes, yes) | (704,384) | FINE HORIZONTAL | COARSE HORIZONTAL from f254, **CRAWLING +2 rows/frame** |

On the answer family's `0x3dc0` the near-black area fraction moves 4.33 → 38.90 % (9.0×), 1.78 → 37.73 %
(21.2×), 0.49 → 37.55 % (**76×**) and 0.45 → 37.58 % (**83×**) on the four cells — the 704 pair has the
cleanest baseline in the container, so the H_U-positive outcome carries the strongest signal.

**ORIENTATION IS VALID IN EVERY FRAME. PITCH IS VALID IN THE CLEAN WINDOW** (f214..236, where both CLUT
families draw: 67/67 meshes, 24,917 tris in the marked cast), **and after it only on column 704 and only
by MOTION.** A late capture answers B and may not answer A — which is still a strict gain over cast 1,
which answered neither. So: **capture from the very start of the effect.** §5's "cast it FIRST and ALONE"
was violated on its face last time.

* **HORIZONTAL on the answer class** → B is applied, cast 1's null is fully explained, and **R_UOFF in
  `second-array-lead\REPORT.md` §3 must be re-opened** (its closure rests on a claim §9.3 shows is false
  under the texel convention). Pitch then says whether A is applied too.
* **VERTICAL on the answer class** → H_U refuted on this container; A alone answers, on pitch, exactly as
  cast 1 intended.
* **Orientation clear, pitch ambiguous** → B answered, A not. Report it that way; do not round it.
* **Control family blank** → not interpretable. Discard, as in cast 1.
* **VISIBLE but UNGRATED on every class** → cast 1's third outcome again — but with all four cells of the
  page marked **G1 can no longer explain it.** What is left is a displaced upload, a cached decode, or a
  cells→VRAM mapping that is not what the container declares, and the canary separates "resident but the
  marks are elsewhere" from "not resident".
* **The confound is unchanged**: A is perfectly confounded with CLUT and blend (20/20, 7/7) and B nearly
  so (19 of 20). The reportable claim is always *"something in the second array moves the sampled CELL"*,
  never "H_V confirmed" or "H_U confirmed".

### 10.5 What is staged, and where

| artifact | path |
|---|---|
| the instrument (to move into tier-w) | `…\u1-second-array\cast2\u1_cell_probe.py` |
| marked container + PROTOCOL.txt + derivation | `…\u1-second-array\cast2\cellprobe\` |
| prediction panels (5 PNGs) | `…\u1-second-array\cast2\predict-cast2\` |
| build/derivation harness — **not part of the shipped file** | `…\u1-second-array\cast2\build\` |

```
py u1_cell_probe.py                     # CAST 2 (default): stages container + protocol + derivation
py u1_cell_probe.py --cast 1 --root <d> # regenerate cast 1's container byte-for-byte (regression)
py <scratch>\cast2\build\verify_bytes.py        # the INDEPENDENT byte proof (does not import the probe)
py <scratch>\cast2\build\roll_check.py          # the ROLL constants, re-derived from the s76 read
py <scratch>\cast2\build\predict_u1_cast2.py    # the five prediction panels
py <scratch>\cast2\build\derive_design.py       # every design number, with its citation
py <scratch>\cast2\build\derive_blurprice.py    # the blur curve that picks the pitch pair
```

**The panels** (`predict-cast2\`) render every surface from its own GEOM UV stream under all four
hypothesis pairs, plus a **pre/post-f237 sheet** showing the roll's effect on each read. The sampler IS
G1: one 256 × 256 page assembled from the four cells, sampled at `page[(v + A_on·A) % 256][(u + B_on·B)
% 256]`. **A and B are parameters, never the constant 128** — cast 1's one renderer defect — and the
sheet computes and prints the proof: the (A=0, B=0) controls are **pixel-identical across all four
panes**, diff 0.

**Location independence is proven, not asserted**: run from a simulated tier-w layout (temp dir plus a
junction to the real kit, with both roots resolving inside it) the container sha is `424761cd…`,
identical to the SCRATCH staging, and the two PROTOCOL.txt bodies diff clean apart from their path lines.

### 10.6 The byte proof

```
AUTHORED          25,158 B  =  24,576 stripe  +  582 canary
stripe ∩ canary        0 B
already 0x00 in stock  143 stripe bytes;  already the ink: 0 canary bytes
CHANGED vs stock  25,015 B  =  4.507 % of the container
outside the authored sets 0 · missing 0 · wrong-value 0
SET EQUALITY  changed == {o ∈ stripes : stock[o] ≠ 0} ∪ {o ∈ canary : stock[o] ≠ ink}  →  True
length 555,008 → 555,008;  the probe still parses as an `so` container
0 changed bytes lie outside the four marked cells
```

Run twice: once inside the probe, once by `verify_bytes.py`, **which does not import it and restates
`MARKS`, the canary geometry, the joint census and the page span on purpose** — so a drift between the
instrument's constants and this study's is a loud disagreement rather than a silent agreement. Both agree
exactly.

### 10.7 What the pins gained, and what the rehearsal exercised

`pin_source` still refuses by name, by stock sha, by both 640 cells' depth/channel/offset/cover, by the
column-640 slot count and A histogram, and by the wrap-record identity. Cast 2 adds four, and **each was
exercised by defeating it one at a time**: the **B and joint (A,B) histograms**; **column 704 must have
ZERO binding slots**; the 704 pair's **file offsets plus the kit's own DEPTH-UNKNOWN REFUSAL, pinned
positively** (a container where they resolve has a second-column binder and needs the G1 argument
re-derived); and the **page span itself**, with the byte↔texel map asserted over all 256 texels of the
page. ★ ef407, the structural near-clone, is refused under BOTH casts.

The deploy rehearsal (§1 item 7, against a temp folder the game never reads) ran twelve gates green:
both ledger branches, both ORDERS including the §8.2 stale-snapshot order, revert twice on each, the
`ModFileList.txt` refusal with zero files written, both foreign-`--from` refusals, the structural pins
with the sha pin defeated, the four cast-2 pins defeated one at a time, and the `--cast 1` guard rails.
**`--cast 1` refuses `--deploy` outright and refuses to run without an explicit `--root`** — its default
root holds the artefacts §9's read was scored against, and regenerating over them would replace the
artefact with a reproduction of it.

### 10.8 The revert ladder — unchanged, with one addition

Unchanged from §7, with **a per-CAST staging root** (`…\cast2\cellprobe`) because the ledger markers and
the emitted revert live in the root and two casts must never share one. `ef038` is ABSENT now, so the
ledger will record `pre.existed = false`, the revert **DELETES**, and the resting state afterwards is
stock. **Revert BEFORE any `summon-reskin deploy` touches this root** — §2, THE LEDGER TRAP. Cast 1's own
root and its `revert_probe.py` are untouched and stay consistent.

**Resting state while this is staged:** ef038 override ABSENT (= stock, verified), `ef211` untouched, rows
192–204 on the bench, every cast-2 artifact under `…\u1-second-array\cast2\`. Nothing was written to the
install, the repo or the Memoria clone.

### 10.5 Verifier corrections (C1-C6) and residual risks — THE READING RULES, folded before any scoring

**All six corrections are wording-level; none changes a container byte. C1 and C2 are load-bearing for
the read and the scorer must honor them over any conflicting sentence in PROTOCOL.txt or the draft
above** (recorded verbatim in `…\cast2\PROTOCOL-CORRECTIONS.md`):

All six are WORDING-level, in `PROTOCOL.txt` and the study §10 draft. None changes a byte of the container, the marks, the pins or the capture instructions, so none blocks the deploy. C1 and C2 should land before the read is scored.

C1 (PROTOCOL, "THE THREE JOINT CLASSES" and question 3) — 0x79168 is framed as a control that "MUST show a VERTICAL grating". It is not a control; it is the cast's ONLY discriminator of the A->v / B->u LABELLING. Under a swapped labelling (the halfword named A moves u, B moves v) the 19 answer readers STILL land on (704,384) FINE HORIZONTAL — the answer class cannot tell the two apart — and only 0x79168 changes, to COARSE HORIZONTAL. Its own UV supports the read (angle median 89.8 deg, min 78.1). Reword to: "record its ORIENTATION. VERTICAL confirms the A->v / B->u labelling. HORIZONTAL is a RESULT — the halfword labelled A is the one that moves u — not a control failure and not grounds to discard."

C2 (STUDY §10.3 and the VISIBLE-but-UNGRATED branch in both the protocol and the study) — the residency canary does NOT close honest limit 3 in the branch it is sold for. The canary lives inside the four marked cells (byte proof: 0 changed bytes outside them), so canary-invisible <=> marks-invisible. In the "the texels came from somewhere else" branch the canary is equally absent and cannot separate "resident but the marks are elsewhere" from "not resident". It adds real power only where the grating is blurred or unresolvable but a 12x12 blob survives (sigma >~ 4 px). Rewrite "the canary then says which" to that narrower claim.

C3 (PROTOCOL, "THE PREDICTED READ PER CELL") — the canary drops the control cell's full-transparent-ROW count: stock 4 -> stripes-only 7 -> with-canary 1. The headline statistic (COLUMNS 0 -> 48) is untouched, but the printed "4/0 -> 1/48" reads like a defect without one line saying the canary is what ate the three rows.

C4 (PROTOCOL, the roll section) — add: after the 704 roll a wrapped COARSE band can present as FIVE runs, two half-width, at some phases (measured at r=16: tops [0,26,58,90,122], thicknesses {6,12}). Harmless under DO-NOT-COUNT; a scorer counting bands would trip on it.

C5 (PROTOCOL, "RECORD THREE THINGS SEPARATELY") — the branch list has "orientation clear, pitch ambiguous -> B answered, A not" but not the converse. Two of the six pairs are separated by ORIENTATION ALONE, and the perspective floor (2*atan(cos tilt): 53 deg at 60 deg tilt, 29 at 75, 20 at 80) means a strongly foreshortened surface can lose orientation while keeping pitch. Add "pitch clear, orientation ambiguous -> A answered, B not".

C6 (DISCLOSURE, protocol scale note and study §10.1) — say out loud that 3.12 px/texel inherits cast 1's 147,000 px disc mask, which §9 records was NEVER attributed to record 0x29dbc (per-record attribution failed by two methods, IoU ~ 0.70). My model-space route reproduces 2.89-3.21 px/texel but from the same 147k input, so it is a consistency check, not an independent anchor.

**Residual risks, stated before the cast:**

R1 SCALE. If the true on-screen scale is materially smaller than 3.12 px/texel (see C6 — the anchor is an unattributed mask), the FINE class at ~6 px feature is likely unresolvable and the cast degrades to orientation-only. The protocol already handles that outcome; it just should not be a surprise.

R2 "PITCH BY MOTION" AFTER f254 IS A WEAK READ. Distinguishing a crawling COARSE band from a static one on a surface that is itself rotating and translating under the battle camera is hard. Treat post-clean-window A as corroboration only; the A answer really does live in f214..236, which is ~23 effect frames and only ~134 of the cast's 661 marked-page meshes. Capture from the very start of the effect, per the protocol.

R3 THE CONTROL IS BETTER BUT STILL NOT LOUD. 36.7% of each control reader's own opaque texels are removed, but the rendered panes look subtle because the 0x3D40 shard is already lacy. If the control family scores blank again, the protocol's "discard" rule fires and the cast is spent — and cast 2 does not repair the fact that this arc has never captured a STOCK reference of these surfaces (§9.1 step 3 is still unspent). The new bright-family control 0x79168 is the real mitigation.

R4 CELL-LOCAL WRAP CONFLATION, INHERITED AND UNRESOLVABLE HERE. If the engine wraps u or v modulo 128 (the CELL) rather than 256 (the PAGE), then "applied" and "not applied" are the identity and produce the same screen class. A VERTICAL/COARSE read therefore means "H_U is inert ON THIS CONTAINER", never "the engine never displaces u". The protocol says "refuted on this container"; keep it that way.

R5 THE CONFOUND IS UNCHANGED. A is perfectly confounded with CLUT and blend (20/20, 7/7) and B nearly so (19 of 20 A=0x80 slots carry B=0x80) — I re-derived the joint-by-CLUT table: (0,0) is 7/7 on 0x3d40, (0x80,0) is 1/1 on 0x3dc0, (0x80,0x80) is 19/19 on 0x3dc0. The reportable claim stays "something in the second array moves the sampled CELL".

R6 CLUT PROVENANCE STILL UNTRACED (§9.3 honest limit 4). The two CLUT strips are not among ef038's 12 declared rects, so every "how a zeroed texel looks" statement — dark bands vs holes, and the canary's colour — rests on palettes whose upload path was never traced.

R7 5% OF FACES HAVE DEGENERATE UV. 86 of 1,718 faces have a dP/du - dP/dv angle under 30 degrees (52 under 20), all on shard tails. Orientation is unreliable on those slivers; score the disc, the shard bodies and the icicles, not the tails. Zero disc faces are affected.

R8 THE ONE ROLL DELTA OF +112. `roll.reconstruction.json` records column 640's deltas as {+1: 141, +112: 1} — one frame jumps 112 rows. It changes nothing for a roll-invariant vertical grating, and is why the +112 frame is not worth chasing, but it is a fact in the reconstruction that no text mentions.

R9 THE `--cells` SEAM. `generate(..., cells=[...])` can write a strict SUBSET of the four marks and the legend records `written: false` for the rest; the CLI exposes `--cells`. A partial run would stage a container whose PROTOCOL claims four marks while the bytes carry fewer. The byte proof and the legend would both show it, but nothing REFUSES it. Deploy without `--cells`.


---

## 11. ★★ CAST 2 — CAST, READ, GAP-CLOSED: **THE SECOND ARRAY IS APPLIED.** `B_ANSWERED_A_NOT` (0.84)

Owner video `shiva_u1.cast2.2026-07-31.mkv` (1,134 unique frames), read by two scoring lenses, an
adversarial verifier (0.82), a gap-closure round on the critic's two load-bearing findings, and a
second critic pass. Full record + BOTH addenda: `…\cast2-read\REPORT-U1-CAST2.md`; owner figures
`cast2-read\annotated\` (start at `00-HEADLINE-the-read.png`). Timing anchored structurally (the
PRIM-98 full-screen TILE frames matched to the video's blue washes, nine consecutive frames exact).

**THE VERDICT — U1 IS ANSWERED POSITIVELY ON THIS CONTAINER**, in the confound-limited wording §4.4
demands: *something in the second array displaces the sampled CELL* — by **+128 texels in u, exactly
one 8bpp column, 640→704**. The carrying measurements, reproduced exactly by every pass:

* **S_SPIKE — labelling-independent, and it stands alone.** 16/16 answer-window frames HORIZONTAL
  (DELTA 88.3–89.8° against a measured body axis of 89.6–91.7°), backed by instrument-free profile
  statistics (ROW profile periodic at 28–73 px, pk/med 8.7–15.6; COLUMN profile a single shading
  lobe) and direct inspection. Every one of the 27 readers binds column 640, so bands ACROSS the body
  = a column-704 cell sampled = unreachable with the second array inert.
* **S_BLADE** (the wrap-reader pair), clean window: 14/18 HORIZONTAL, DELTA 78.3–89.4°, 4 borderline.
* **The mark identified photometrically on screen**: over bare cave (24.3 luma) the plate's dark
  bands measure p10 42.2–42.4 against 39.7 predicted for `clut 0x3dc0` entry 0 = rgba(8,16,32) drawn
  additively — the cutout (24.3) and abr-0 (19.8) alternatives excluded. The marked page's own zeroed
  texels, rendered — this also closes cast-2 residency without the canary.
* The projection-independence check ran on the video itself: the two carrying surfaces lie ~90° apart
  on screen and give the same texture-space answer.

**THE SWAPPED LABELLING — 0.68, carried separately.** `0x79168` (A=0x0080, B=0x0000) reads
HORIZONTAL, which the declared A→v/B→u labelling forbids — §10.5 C1's RESULT branch: **the halfword
the container labels A is the one that displaces u.** The closure round removed the loudest
objection by measurement: the two-layer composite (built from the container's own texels, palettes
and blends; harness validated by reproducing all 12 calibrate8 cells to Δ 0.0000) shows a
true-HORIZONTAL bright layer plus the co-drawn `0x3d40` twin falls BELOW the control meter's refusal
floor (2.99 < 3.088) — so that meter's "ambiguous" was never evidence against HORIZONTAL — and the
VERTICAL counterfactual cannot reach 22 of the 26 observed frames (ceiling 0.58 vs observed
0.49–1.93). NOT fully reproduced: an unexplained 1.5–2× twin-weight factor remains, which is why the
labelling sits at 0.68 rather than riding the verdict. It also refutes cell-local u-wrap on this
container (u+128 landed in the NEXT column, not back on 640).

**PITCH — the v axis — UNRESOLVED.** Coarse-vs-fine never separated on the scored surfaces (the
plates unscorable; §10.5 C5's partial branch fired exactly as designed). Whether the OTHER halfword
is applied on v stays open; f235–237 carry no marked-page draw, so §10.2's roll-onset signature was
unobservable as specified.

**THE EXCLUDED SURFACE, disposed honestly.** The contested left-plate crop turned out to be **the
DISC (`0x29dbc`) carrying the mark** — but its measured DELTA (32–41°) sits at the §10.5 C5
perspective floor for its tilt, non-discriminating in either direction; dropped from the orientation
vote for that measured reason. ⚠ The re-check critic then found the closure's own prose defects —
the strip-only control was never actually scored (its MINPIX gate rejected every frame), the
tilt-72.4° figure has no traceable measurement, the attribution ranges hold for 16/20 not 20/20
rows, and two "clean window" frame sets differ between documents — **recorded verbatim in ADDENDUM 2
as standing limits (THE REGRESS STOP)**: the surface stays excluded under every disposition, no
finding touches the surviving basis, and the arc stops re-litigating prose while the carrying
numbers reproduce.

**WHAT MOVES AND WHAT DOES NOT.** No constant moves; nothing is promoted. The confound stands (A
20/20 with CLUT+blend, B 19/20), so H_U-vs-H_V attribution is NOT made; R4's cell-local-wrap caveat
still applies to v. **Owner decisions now live**: (1) re-open R_UOFF in
`second-array-lead\REPORT.md` §3 — its closure rested on "both u-shift conventions move slots OFF
declared columns", refuted here under the texel convention; (2) whether the kit's attribution/refusal
surfaces need to model a second-array u-displacement (a reader's EFFECTIVE cell ≠ its bound cell on
displaced slots — the census/licensing consequences are real but unscoped); (3) whether the pitch
axis is worth a cast 3 (a v-axis-only instrument on a G1-passing design), or rests until a vehicle
needs it.

**Resting state:** ef038 override DELETED (= stock, verified; `ef211` untouched), rows 192–204 stay,
both casts' videos/frames/logs/analysis under `…\repaint-w6b\u1-second-array\`, the s76 engine
round permanent (`memoria-patches/s76-sfx-state-payload.patch`). `ORDER_UNMEASURED` and every kit
constant ship exactly as they were.


### 11.1 THE IMPACT SCOPING — the data under owner decision (2). Critic: ok=true, ZERO gaps

Offline, conditional-altitude throughout ("IF the ef038 mechanism generalises"), both labellings
side by side, v not modelled. Record: `…\u1-second-array\impact-scoping\REPORT-IMPACT.md` +
`u-displacement-impact.tsv` (293 rows × 40 cols). Calibration: exact reconciliation with the dual
census (372/502/126/309/649/28), 309/309 row identity with census-B, and ZERO difference from the
kit's own `cell_readers` at zero displacement over 80/80 containers. Both sanity checks pass (ef038
reproduces the cast, controls included; ef211's dome binder is A=0/B=0 = undisplaced, so the W6b-2
flagship stays correctly explained).

* **The exposure is concentrated and SILENT**: 16 (SWAPPED) / 19 (ORIGINAL) of the 187
  so-uv-LICENSED cells would lose EVERY effective reader — `export-art` hands an author those pages
  as fully-licensed TODAY, and a perfect repaint on one would be invisible with no error anywhere.
  Named individually in the report. Granularity matters: a cell only goes dark if EVERY reader
  displaces — ef038 (640,256) kept its 7 undisplaced controls, which is exactly why cast 1 read
  VISIBLE_UNBANDED rather than blank.
* **Under SWAPPED every displaced sample lands on a DECLARED cell (144/144, 0 undeclared)** — and a
  new corpus-scale asymmetry points the same way as the screen: 0/156 displacing slots leave their
  page vs a permutation null of 16.6 (P<0.0005), while ORIGINAL sits dead on its null (40/224).
  Carried as an OBSERVATION of C3's non-discriminating class — it measures no engine; it must not
  choose the labelling for a derivation.
* ★ **THE ef424 ORDER-CELL LEAD** (conditional): `cell.s0.x448_y384`'s ONLY incumbent reader
  (0x2ec24, forced part, A=0x0080/B=0) displaces to column 512 under SWAPPED — leaving the order
  cell with no effective reader. A U-axis explanation for the k=2 mark that was never positively
  located (~0.35), where the refuted V-story baked off the page. A lead, not a claim.
* **Erratum, flagged not overruled**: §9.3's H_U corpus stats "224/224" and "153/153" do not
  reproduce under the page predicate (184/224, 135/153); its "150/153 declared" reproduces exactly.
  The intended predicate is not recoverable from the text.

**THE RECOMMENDATION (the round's, endorsed): OPTION 2 — DISCLOSE/ANNOTATE, strictly additive** —
`so_record` gains the second-array pairs it currently discards, `CellHazards` gains an informational
per-reader field naming both candidate effective columns, one appended refusal class fires on a cell
ALL of whose readers carry a mover (the `spill-vs-own-page` precedent), the conditionality triple
(0.84 / 0.68 / v-unresolved) carried IN the quotable constant per the `ARRAY_CAVEAT` pattern. No
constant moves, no emission changes, every re-derivation-pinned gate keeps measuring its population.
**Option 3 (derivation modelling) stays gated behind one cheap instrument: log `tag->u0..u3/v0..v3`
at `SFXRender.cs:342-380`** (the §9.3-named field) — a log-only cast then settles H_U per-slot
without a screen read. Options 1/3 and the gate are the owner's call; nothing here was implemented.


---

## 12. ★★★ THE s77 UVR READ — THE MECHANISM, MEASURED. Both halfwords, both axes, 0.97

The owner-authorized s77 engine round (`memoria-patches/s77-sfx-uv-range.patch` — the UVR row:
per-mesh min/max of the primitives' OWN u,v bytes, joined 1:1 to textured MESH rows) went live, and
ONE stock log-only Shiva cast closed the arc. Log `capture-logs\sfxmeshprobe.s77-uv-cast.log`
(8,587 UVR rows, on the predicted budget); read by the parent, adversarially verified by an
independent pass whose critic returned **ok=true with ZERO gaps** (the arc's second flawless pass);
record `…\u1-second-array\s77-read\REPORT-S77-READ.md`, scripts + JSON beside it.

**THE MECHANISM (0.97 on this container): the second array is a per-slot texel displacement, baked
into the primitive stream — pair position 0 displaces u, pair position 1 displaces v, +0x80 = +128
texels each.** All four cells of the (A,B) 2×2, zero residue, each on an independent population:

| (pos0, pos1) | population | logged u | logged v |
|---|---|---|---|
| (0, 0) | the 7 controls, whole key, 48 frames | raw [0,126] | raw [1,127] |
| (0x80, 0) | rec `0x79168` ALONE, 25 wrap-frames | **raw+128** [130,253] | raw [1,255] |
| (0, 0x80) | rec `0x86700`, 53/53 frames | raw | **raw+128** (vMin 193 = 65+128) |
| (0x80, 0x80) | the 19 confined answer readers, 112 frames | **+128** [128,255] | **+128** (vMin 129 = 1+128) |

The fourth population (`0x86700` — the one reader cast 2's S7 predicted invisible) is what kills the
last rival model ("pos-0 gates everything"): `MODEL_II_MATCHES = false`. The wrap reader alone
settles the labelling with no other family and no model: it carries pos0=0x80/pos1=0 and moves in u,
not v — under the container's declared A→v/B→u labelling it could not move in u at all. **The 0.68
screen inference is RETIRED in favour of a measurement.** The verifier also ran an attack nobody had
named — the u-is-low-byte decode every prior round ASSUMED — and measured it via the control
family's asymmetric raw bounds (u [0,126] vs v [1,127]: only one byte order predicts that). Four
named attacks all survived structurally (no SPRT contamination — the FILTER bit discriminant is
provable, not observed; repeat-render dedup identical on 18/18 keys; family mislabelling impossible
by construction — the key is computed from each primitive's own tpage+clut; the 25-frame set is an
IDENTIFICATION, u [130,253] being unreachable by any confined reader).

**What this closes, at its earned altitude:**

* **Cast 1's null — fully mechanical, no free parameter** (0.97 this container): 20 of 27 readers
  sample column 704 (unmarked in cast 1); the 7 that sample the marked cell render their mark as
  transparent HOLES (§5 warned in writing they'd be scored blank). VISIBLE_UNBANDED was the correct
  observation of a page two-thirds unmarked and one-third invisible.
* **The pitch axis (§11 "UNRESOLVED") — resolved**: v IS displaced, read directly on two independent
  populations. A pitch-axis cast 3 is NO LONGER NEEDED.
* **Cast 2 retro-validated three ways**, and its open per-record attribution closed for the 0x3DC0
  layer: the 25 wrap-alone frames sit inside cast 2's own S_BLADE clean window (f229–234, 162 prims
  = 6×27) — Gap-B's two-layer weld is now measured, not modelled.
* **R_UOFF**: its refutation-of-closure changes CLASS (screen → byte stream). **The ef424
  order-cell lead's PREMISE is confirmed** (the lead itself still needs its own container's read).
* **The Option-3 gate (§11.1) is MET on ef038** — the instrument the scoping demanded is built,
  deployed, cast, and read.
* ⚠ **The pre-registered read was UNDER-SPECIFIED and is recorded as such**: the README's branch A
  (`uMin ≥ 128`) and branch B (`uMax < 128`) were both observed — split by FAMILY, which is the
  in-cast control doing exactly its job — but the pre-registration as written enumerated neither.
  The substantive finding is the strong branch: baked into the prim stream, NOT sampler-side.

**Binding limits:** ONE CONTAINER, ONE CAST — the only thing between this and a law; a second
container's log-only cast makes it general. Magnitude-vs-flag not separable here (ef038 carries only
{0, 0x80}; any container with another value settles it in one cast). Wrap/clamp behaviour untested
(every displaced span fits the byte). The 0x3D40 pool still doesn't isolate `0x79ae8` per-record.

**★ THE STALE-TEXT LEDGER — OWNER DECISIONS, nothing touched** (full detail in the report §limits):
(A) `depth_attribution.U_DISPLACEMENT_CAVEAT` — riders (2) "labelling 0.68, neither preferred" and
(3) "v axis unresolved, not modelled" are now the OPPOSITE of the measurement, and "0.84" is the
wrong altitude for u on this container; editing it is a COORDINATED change (7 repaint call sites +
reskin + 4 test assertions + u1_gates pins, and the constant may never contain `%`).
(B) `U_DISPLACEMENT_ACK_WARNING` inherits all of it. (C) §11's "0.68, carried separately" /
"PITCH — UNRESOLVED" / owner-decision (3), and §11.1's Option-3 gate sentence — superseded by this
section. (D) `CHANGELOG.md` quotes the caveat's framing. (E) `second-array-lead\REPORT.md` §3 +
addendum — basis superseded in class. **Updating (A)+(B) is the natural follow-on to the Option-3
decision; (C)–(E) are prose corrections this section already supersedes in place.**

> **★ APPLIED (the ledger above is CLOSED; this stamp is the only edit to this section).** (A)+(B)
> were rewritten to the 0.97 two-axis read across 6 files, and (D) with them. NO number, NO
> derivation and NO emitted byte moved — `depth_attribution.py` and `reskin.py` are string-stripped
> **AST-identical** to their pre-edit state, the corpus roll is page-for-page and refusal-for-refusal
> identical over all 372 containers, and the 4 frozen boards re-ran byte-identical. The pins were
> STRENGTHENED, not re-aimed: absence-assertions on the four refuted tokens now make a silent revert
> fail loud. Two adversarial passes ran; one caught a number the rewrite MINTED wrong (`60` of 151
> movers not-8bpp — the true value is **52**, `{4:41, 8:99, 15:11}`), re-derived independently three
> times and corrected before commit. Riders now standing at FIVE, not three: generalisation, the
> OPERATION (add-128 vs top-bit-toggle — indistinguishable on ef038's `{0,128}`), depth, wrap-clamp,
> and per-slot-only-where-slot-equals-record. (C) and (E) stay as written — dated records this
> section supersedes in place.



**Resting state:** install stock everywhere except the engine (s76+s77 permanent instruments, both
arches `44d4b974…`, backups `20260730-222511` / `20260731-192628`); rows 192–204 stay; every log,
patch, report and script archived under `…\repaint-w6b\`. No kit constant moved.
