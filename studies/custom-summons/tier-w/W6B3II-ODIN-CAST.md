# W6b-3 (ii) — THE ODIN CHANNEL-A CAST LADDER. ef424 `Odin__Short`, bench rows 203/204

> ⚠ **STATE, re-read at every session start — this banner is stale the moment a cast runs.**
> **CAST A ran and was positive (§7). CAST B is DEPLOYED and LIVE** —
> `…\FF9CustomMap\FF9_Data\SpecialEffects\ef424` = `69ed527d…` — **and its read REFUTED its own
> discriminator (§8).** **CAST C is BUILT AND STAGED, NOT DEPLOYED**: `…\ef424-channel-a\stage-c\`,
> sha `0650b968…`. No commit, no `Memoria.ini` edit, no relaunch needed. Sections 1–6 are cast A/B's
> sequence and are kept as the record; **§8 is the live one.** ⚠ Cast C's revert restores CAST B, not
> stock — §8.4.

**WHAT IS BEING MEASURED.** `cell.s0.x704_y384` is bound by exactly one thing in the container: entry
slot 1 of the multi-part `so` record 0x2f9a4 (P = 2). `page_depth_view` is ABSENT for that whole column,
so **CHANNEL A is the only channel that states its 8 bpp** — and channel A has never put a texel on
screen (0 hits / 4 misses / 2 vacuous passes over six named cells). Two questions, in this order:

| | question | instrument | answer shape |
|---|---|---|---|
| **CAST A** | is the cell DRAWN at all? | `odin_cell_probe.py` — zero stripes, 10 on the verdict cell, 2 on the order cell | banding / clean |
| **CAST B** | is channel A's 8 bpp the DRAW depth? | `odin_channel_a.toml` — 5 ink bands (byte `0xFF`) | ~~clean / pin-striped / wrong-hue~~ **VOID — see §8** |
| **CAST C** | is channel A's 8 bpp the DRAW depth? | `odin_channel_a_c.toml` — the SAME 5 bands, ink byte **`0xF0`** | **salmon bands / no spearhead at all / violet** |
| **RIDER** | which part reads which array entry? | the same two band COUNTS, per surface | identity / reversed / vacuous |

**BINDING-IS-NOT-A-DRAW gates the ladder, not the reverse.** A negative depth read on an undrawn cell
measures nothing, which is the mistake this tier has already paid for twice (two ef211 casts, one ef429
frame sweep). **Cast A first. Always.**

**AND THE RIDER'S RESULT IS NOT A VERDICT.** `ORDER_UNMEASURED` (`summons/depth_attribution.py`) is a
call-sited constant, and the kit's own disclosure says the entry's order within the array is unmeasured.
Whatever the screen shows, **write it in the study and change no constant.** Promoting it is a separate
gated decision with its own evidence bar; one cast on one container is an observation.

---

## 1. PREFLIGHT — W6b-1 §5.5, adapted, in this order

Everything here is **verify, never assume**. Observed values are what this session measured; the folder
is shared mutable state and 18+ sessions run concurrently, so **re-measure at deploy time**.

1. **`Memoria.ini [SfxHybrid] Enabled = 0`.**
   Observed `Memoria.ini:451 Enabled = 0`, `:452 EffectId = 227`. It is pinned to 227, so even armed it
   would mask nothing on ef424 — **which is the worst kind of wrong**, because the ladder would look
   fine while the hybrid drive posed a model nobody asked about. Check the number, not the section.
2. **No `ModFileList.txt` in the mod folder — THE SILENT-FALLBACK LAW.**
   `TryFindAssetInModOnDisc` TRUSTS that list and never calls `File.Exists`, so an unlisted override is
   INVISIBLE and cast A would read as a clean negative for a reason that has nothing to do with drawing.
   Observed ABSENT in both `FF9CustomMap` and `FF9CustomMap-world`. `odin_cell_probe.py --deploy`
   REFUSES if one appears, by name.
3. **A first-deploy snapshot of whatever the folder holds, once per root.**
   Observed `FF9CustomMap/FF9_Data/SpecialEffects/` holds exactly one entry — **`ef211` as a FILE**,
   530,432 B, sha `cbcc9fde…`, mtime 2026-07-28 23:35 = the W6b-2 pool wheel, that ladder's documented
   resting state. **`ef424` is ABSENT**, so this ladder's revert is a DELETE, and the resting state
   after it is stock.
   ⚠ **Recon correction, carried deliberately:** the recon slice reported this tree as holding "only an
   EMPTY ef211 dir". `ef211` is a **file**, not a directory — an override is `…/SpecialEffects/ef<NNN>`
   written as one file, which is the path both the probe and the kit's deploy use. The mtime predates
   the recon, so this is a read error rather than drift; the lesson is that the folder is live and the
   state must be read at deploy time, which is what `--deploy` prints before it writes anything.
4. **`[SfxProbe]` armed, and its log ARCHIVED TO SCRATCH THE SAME SESSION.**
   Observed `Memoria.ini:440 Enabled = 1` with `CapturePrims = 1`. The install is shared: a campaign
   deploy wiped a probe mid-ladder once already, and a log that is still only in the install is a log
   somebody else can overwrite. Copy it into
   `C:\gd\SCRATCH\summon-format\repaint-w6b\capture-logs\` before the next cast, not after.
5. **The live ef424 sha == the stock corpus sha.**
   Observed: the kit's own resolver reads `x64/FF9_Data/resources.assets` and returns
   `6a3cb4d7fb26c7cd5c497b2fd4b2364039aabb0e491ed7b26e7b6060e0400773` — **identical to the corpus file**
   `C:\gd\SCRATCH\summon-format\ef424.bytes`, which is the value `odin_channel_a.toml`'s
   `expect_sha256` guards. Note what that check covers: it reads the BASE container (Steam / Moguri
   drift), not the mod folder. The override's own absence is item 3's job.

    py -m ff9mapkit summon-reskin export-art --ef 424 --out <a throwaway local dir>   # prints the sha

6. **REHEARSE THE DEPLOY PATH FIRST — calibrate the instrument before judging with it.**

    py odin_cell_probe.py --deploy --mod-folder <a temp dir>\FF9CustomMap --root <a temp probe root>

   It prints `*** REHEARSAL`, exercises the whole ledger (`pre.ABSENT` **and** the
   already-present branch), verifies the readback sha and emits the revert script — against a folder
   the game never reads. **This is not ceremony: the first rehearsal of this path caught a real
   defect.** The emitted `revert_probe.py` interpolated the install path into its own docstring, so
   `…\Users\…` became an invalid `\U` escape and the script **did not parse** — it would have failed at
   the one moment it matters, immediately before the kit deploy. Paths now go through `%r` into code
   lines only, and the generator `compile()`s the script it just wrote. Rehearse both branches, and
   confirm the revert is idempotent (run it twice).

---

## 2. THE DEPLOY SEQUENCE — and THE LEDGER TRAP

```
  0.  bench    py studies/custom-summons/rung8-epic/bench/build_rung8_bench.py --clean --check
              py tools/deploy_field.py studies/custom-summons/rung8-epic/bench/rung8.field.toml --id 30301
  1.  RELAUNCH FF9                                     <- Actions.csv is a REGISTRATION change
  2.  cast A   cd studies/custom-summons/tier-w
              py odin_cell_probe.py --deploy           <- snapshots, writes, prints the readback sha
  3.  READ IT  (section 4).  Archive the [SfxProbe] log.
  4.  *** py C:\gd\SCRATCH\...\ef424-channel-a\cellprobe\revert_probe.py ***   <- BEFORE step 5
  5.  cast B   (cwd = ff9mapkit\)
              py -m ff9mapkit summon-reskin deploy ../studies/custom-summons/tier-w/odin_channel_a.toml ^
                 --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\stage
  6.  RECAST   (no relaunch -- a page upload is itself the cache-invalidating event)
  7.  READ IT  (section 4), then the revert ladder (section 6).
```

**`--out` ON THE DEPLOY IS NOT COSMETIC — IT PINS THE LEDGER.** Omit it and `deploy` re-builds into the
kit's DEFAULT root `C:\gd\SCRATCH\summon-transplant\repaint\ef424\` and writes its
`revert_summon_repaint_ledger_424.py` *there*, not beside this ladder's other artifacts — so section 3's
table would be describing a staging root the deploy never used, and the revert in section 6 would have to
name a different one. (The rebuild is deterministic — sha `69ed527d…` either way — so the risk is a lost
ledger, not a wrong container.) Rehearsed end to end against a temp mod folder: deploy → `absent` ledger
→ revert **deletes**, exit 0.

### ⚠ THE LEDGER TRAP — step 4 is not housekeeping, it is the load-bearing line

`summon-reskin deploy` takes a **FIRST-DEPLOY SNAPSHOT per root, once, and never overwrites it**. Deploy
the ink cast while the probe container is still live and that snapshot records **THE PROBE** as the
pre-state — and the kit's revert then restores the probe, *forever*, as the resting state of a mod
folder nobody is looking at any more. There is no error, no warning and no symptom until somebody casts
Odin months later and finds it striped. **Revert the probe first.** The probe's own revert script says
so in its docstring, and `--deploy` prints the same line after it writes.

The same trap in the other direction is why the probe never uses the kit's ledger: it keeps its own
`pre.ABSENT` / `deploy.ledger.json` under its SCRATCH root, so the two instruments can never consume
each other's snapshot.

### Relaunch, exactly once

Rows **203** (`Stock Odin Short`, vfx 424/424) and **204** (`Stock Magic Hammer`, vfx 130/130) are
`Actions.csv` REGISTRATION changes → **one relaunch, before cast A**. They are registered together on
purpose: if cast A comes back negative the ladder falls back to row 204 without a second relaunch.
**The container overrides are HOT after that** — `SFX.Play` re-reads the container and wipes the
decoded-texture cache on every cast, so both the probe and the ink cast are live on the NEXT cast and
so is their removal. Post-relaunch PASS/FAIL: 203 and 204 castable **and** 198–202 still working. If a
previously-working row broke, **STOP** — the 192+ allocator moved and something already deployed shifted.

---

## 3. WHAT IS STAGED, AND WHERE

| artifact | path |
|---|---|
| bench rows 203/204 | `studies/custom-summons/rung8-epic/bench/rung8.field.toml` (committed) |
| cast A instrument | `studies/custom-summons/tier-w/odin_cell_probe.py` (committed) |
| cast B generator | `studies/custom-summons/tier-w/odin_band_stamp.py` (committed) |
| cast B spec | `studies/custom-summons/tier-w/odin_channel_a.toml` (committed) |
| probe container + protocol + revert | `…\repaint-w6b\ef424-channel-a\cellprobe\` (SCRATCH) |
| the order cell's art (+ `art.manifest.json`) | `…\ef424-channel-a\art\` (SCRATCH) |
| the verdict cell's art — **manifest-free on purpose** | `…\ef424-channel-a\art-channel-a\` (SCRATCH) |
| the staged patched container | `…\ef424-channel-a\stage\mod\FF9_Data\SpecialEffects\ef424` |

Regenerate all of it from the committed sources, in this order — no staged byte is committable. **The two
`py -m ff9mapkit` lines run from `ff9mapkit\` (the local package must shadow any editable install); the
two bare `py odin_*.py` lines run from `studies\custom-summons\tier-w\`.** Verified: a full regeneration
in a fresh staging root reproduces every artifact BYTE-IDENTICALLY (art PNGs, both stamped figures, the
probe container `12f041c3…`, the patched container `69ed527d…`).

```
py -m ff9mapkit summon-reskin export-art --ef 424 --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\art
py odin_band_stamp.py
py odin_cell_probe.py
py -m ff9mapkit summon-reskin build  ../studies/custom-summons/tier-w/odin_channel_a.toml --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\stage
py -m ff9mapkit summon-reskin verify ../studies/custom-summons/tier-w/odin_channel_a.toml --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\stage
```

**One structural fact the export lane forces.** `summon-reskin export-art` REFUSES
`cell.s0.x704_y384` by name (`depth-unknown`): `repaint.export_art` calls `scenery_surface` with no
`array_depth`, so the shipped export has no channel-A acknowledgement and therefore no picture for it.
`odin_band_stamp.py` derives that one cell itself through the same shipped primitives with the ack
threaded, and writes it into a **manifest-free** directory — because `_gate_manifest` refuses a target
its manifest carries no record for, and a manifest that *cannot* record the cell must not be allowed to
veto it. On that row the spec's `expect_*` + `expect_sha256` are the whole guard, which is exactly what
the manifest-absent path is for. The order cell rides the full ART-DRIFT guard.

---

## 4. THE CAST PROTOCOL

**Warp `30301` → STEINIV → `Rune` → the row.** (`Rune` is command 35, not Vivi's `Spark` — a pool name
resolves against the BASE csv, so the minted rows seat on Steiniv's learn list.) MP 8, power 30; the
save point at the bench's south edge is there so cast N+1 is cheap. **Capture video, not stills** —
every read below is a COUNT on a moving surface.

**The two surfaces to watch** (record 0x2f9a4's own parts, geometrically unconfusable):

* **part 0 — THE TUBE.** 32 prims, 96 verts, x ∈ [−16,16] y ∈ [−16,16] **z −1028 → −422**: a long thin
  square-section tube shooting away from the camera.
* **part 1 — THE PLANE.** 68 prims, 204 verts, **x ≡ 0**, y −130 → 130, z −422 → 0: one flat billboard
  plane near the origin.

### CAST A — count DARK bands per surface

| what a surface shows | what it means |
|---|---|
| **10** dark bands, a fine ~13-line grating | it samples `cell.s0.x704_y384` — **CHANNEL A IS DRAWN, cast B is armed** |
| **2** dark bands, coarse and unmistakable | it samples `cell.s0.x448_y384` (the licensed `so`-UV column) |
| clean | it samples neither — this cast's own control |
| nothing bands anywhere | **BOUND-NEVER-DRAWN**; go to section 5 |

Read the 448 cell first: **k = 2 at 6 rows is the unambiguous half of this probe**, and its stripes sit
inside the reader's own cover (lines 0..63), so a declared reader must show them. The 704 cell's
canonical k = 10 at 6 rows is a near-50 % grating — the primary signal there is *"the surface goes gappy
at a fine regular pitch"* and the count is the confirmation. If the count is unreadable on video,
`py odin_cell_probe.py --cells cell.s0.x704_y384 --deploy` marks that cell alone and every other cell
becomes its own control (revert in between).

⚠ **THE ONE DEGENERATE AXIS, DISCLOSED.** On the verdict cell cast A's aggregate duty (10 × 6 = 60 rows)
**equals** cast B's (5 × 12 = 60 rows). The COUNT differs (10 vs 5) and so does the POLARITY (dark holes
vs bright ink) — those are the two axes the read uses — but the duty-cycle shortcut the ef211 census
decoded with is **useless here**. *Count the features; never infer the instrument from how much of the
surface changed.* The probe prints this note into its own `PROTOCOL.txt` every run.

### CAST B — judge the INK

| what the screen shows | the verdict |
|---|---|
| **clean bands** | channel A's **8 bpp IS the draw depth** |
| bands present but **pin-striped / textured** | a **4 bpp** read (each ink byte splits into two nibble texels) |
| bands in one **solid wrong hue** | a **15 bpp** read (byte pairs become direct words) |

And the rider, from the same frames: **3 bands on the tube + 5 on the plane** → consistent with identity
ordering (part *k* ↔ entry *k*); **5 on the tube + 3 on the plane** → consistent with the reverse; only
one surface banding → the order read is **VACUOUS** and the depth read still stands. Write it down.
**Change no constant.** `ORDER_UNMEASURED` stands.

⚠ **DERIVE THAT TABLE AT THE MACHINE, DO NOT RECALL IT.** The first draft of these two lines was
**inverted**, which would have written the opposite observation into the study from the same video. The
chain, every link measurable off the user's own container: the binding array in **file order** is entry
**0 → column 448** and entry **1 → column 704** (the tpage words at `0x2f9a4 + 8 + 4k`); the marks are
**3 bands on 448, 5 on 704**; the parts are **part 0 = the TUBE** (32 prims) and **part 1 = the PLANE**
(68 prims), from GEOM `0x2f9bc`'s own primitive stream. Identity therefore means part 0 → entry 0 →
column 448 → **the tube shows three.** A band count is not a mnemonic.

**Expect a THINNING, not a poster.** The verdict cell is 73.6 % hardware cutout and every transparent
texel is skipped, so only 2,311 of 7,680 band texels carry ink — the bands brighten the surface's own
structure at 5 heights. The order cell's 3 bands are dense by comparison (3,942 of 4,608 inked, every
band on lines a reader samples). Read that last clause exactly: the cover is a **halfword set**, not a
line set, so of those 3,942 bytes the build puts 1,694 inside the cover and **2,248 (57.0 %) outside**
it — ~560 sampled texels per band, which is what makes a COUNT readable, where the whole-cell rule's
third band would have landed **zero**. Both figures are bands and never shapes: the verdict cell has
**zero** declared UV cover, so the flatness screen that licenses a shape cannot clear it.

---

## 5. THE FAILURE LADDER

**Cast A negative — nothing bands on any surface.** That is a RESULT: **BOUND-NEVER-DRAWN joins the
ghost table** as channel A's fifth miss, ef424 `(704,384)` by name, and **cast B must not be deployed**
(a negative depth read on an undrawn cell measures nothing). Two cheap follow-ups before conceding, one
deploy each with a revert between: `--placement whole-cell` (a cell's UNBOUND lines may be what the
id-3 program's own primitives draw — the ef429 lesson, and note the order cell's cover stops at line 63)
and `--all` (which cell *do* the visible surfaces read?).

**Then the ef130 fallback, sketched.** Bench row **204** casts `Magic_Hammer = 130`, already registered
in the same relaunch. ef130's verdict cell is `cell.s0.x448_y384`, bound only by slot 1 of the corpus's
widest multi-part record (0x29cf8, **P = 7**), so it re-asks cast A's question on a second, independent
container. It is a **weaker vehicle and was chosen as the second witness, not the better one**: 5 of its
7 entries are unmarkable by construction (column 576 refuses `array-dual-depth`, and no acknowledgement
lifts a dual), its parts overlap heavily in y so an order read cannot separate them on screen, its
part-1 u range spills out of the column at 8 bpp, and — the one that changes the read — its palette
entry 0 is `0x8000`, **opaque black with stp set**, so the cell has NO transparent value and a
zero-write paints BLACK instead of punching a hole. Same ladder, same order (probe → read → revert →
ink), and the cast-A read becomes "count the black bands" rather than "count the gaps".

⚠ **`--from ef130.bytes` IS NOT THE RE-PIN, AND ON ITS OWN IT IS DESTRUCTIVE.** `EFFECT`,
`VERDICT_CELL` / `ORDER_CELL`, `BANDS` and the probe's `GAME_OVERRIDE` destination are **module
constants pinned to ef424**; `--from` moves the SOURCE and nothing else. Passing it alone stages the
ef130 probe as `ef424.cellprobe` and `--deploy` writes ef130's 231,424 bytes over
`…/SpecialEffects/**ef424**` — and on the stamp side it overwrites ef424's art with ef130-derived
pictures, which neither `expect_sha256` (it guards the CONTAINER) nor the ART-DRIFT guard (it checks
the manifest's stock sha) would notice. **Both scripts now REFUSE a foreign `--from` by name**
(`pin_source`: the file must name the module's `EFFECT`, *and* both ladder cells must derive the
channel + depth this ladder was measured on — ef130's 704 cell derives 4 bpp and its 448 cell refuses
without an ack, so it fails both pins). Running the fallback means **editing the constants in both
files** — `EFFECT`, the two cell names, `BANDS`, `SOURCE_PIN` — then re-running the whole ladder.

**Cast B ambiguous** (bands visible but neither clean nor obviously striped): that is the ef446
signature and it means the DEPTH COROLLARY is in play — the array's 8 bpp is what something BINDS at
while the draw reads the same bytes at another depth. Record the frames and stop; do not re-cast with a
second figure in the same deploy, because composing figures is what makes a read ambiguous in the first
place.

---

## 6. THE REVERT LADDER

```
  probe   py C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\cellprobe\revert_probe.py
          -> "deleted <install>\FF9CustomMap\FF9_Data\SpecialEffects\ef424"   (pre.ABSENT: there was none)
  ink     (cwd = ff9mapkit\)
          py -m ff9mapkit summon-reskin revert ../studies/custom-summons/tier-w/odin_channel_a.toml ^
             --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\stage
          -> "deleted <install>\...\ef424" + "summon override revert complete."
             the ledger's own script; ef424 was ABSENT at first deploy, so revert DELETES it
```

⚠ **NAME THE SPEC, NOT `--ef 424`, AND PASS THE SAME `--out` THE DEPLOY USED.** `revert --ef N` with no
spec resolves `ef###_reskin.toml` and routes to the **CLUT/reskin lane's** root — measured:
`revert --ef 424` looks for `…\summon-transplant\**reskin**\ef424\revert_summon_**reskin**_ledger_424.py`
and exits 2 `nothing to revert`, while this texel cast's ledger is
`…\**repaint**\ef424\revert_summon_**repaint**_ledger_424.py`. Today that is fail-safe (nothing happens,
loudly) but the operator would believe the override was removed while the ink cast stayed live on a shared
install; and if an ef424 **CLUT** plate ever exists, `--ef 424` would revert *that* instead. `--out` must
match the deploy's for the same reason — the ledger is found under the staging root, not under the spec.
⚠ And **never `--dry-run` the deploy into the default root as a rehearsal**: a dry run still writes a
`revert_summon_repaint_ledger_424.py` there, baked to its own `dry-run-mod` mirror — a later bare revert
would report "deleted …\dry-run-mod\…" and look like success. Rehearse with `--mod-folder <temp>` instead,
which is what the probe's `--mod-folder` exists for.

**THE RE-TARGETING LAW applies to the ink revert and it is not a formality.** A revert's destination is
a HISTORICAL FACT, not a preference: the plan bakes in the folder its writes landed in and re-targets
ONLY on an explicit `--root` / `--mod-folder`. This ladder's ledger entry records `existed = False`, so
the revert **deletes** — and rebased onto a folder that plate never wrote to, that would delete somebody
else's perfectly good override. Pass `--root` only when you mean it; the resolver prints its answer
either way, so a mismatch is visible rather than acted on.

**What does NOT get reverted:** bench rows 203/204 stay. They are allocated ids on a live CSV, and
removing a row renumbers nothing but strands the next one — rows 201/202 stayed for the same reason and
are the control that shows the 192+ allocator never moved. **Resting state after the ladder:** ef424
override DELETED (= stock), rows 203/204 on the bench, every artifact and every video in
`…\repaint-w6b\ef424-channel-a\`, and the `[SfxProbe]` log archived beside them.

---

## 7. ★★ CAST A — RAN 2026-07-30, AND IT IS POSITIVE

**Owner's report: *"i see a banded javelin shoot down from the sky."*** Video
`C:\Users\skaki\Videos\2026-07-30 08-43-30.mkv` (4.417 s, 1920×1080, 60 fps; the SFX layer updates every
4th frame, so ~66 unique frames). Frames + the whole readout under `scratchpad/castA*`; evidence crops
in `castA/evidence/`, offline part renders in `castA/geom/`.

### 7.1 ⛳ THE CELL IS DRAWN — CHANNEL A PUTS TEXELS ON SCREEN

Measured, not eyeballed, on the impact frames (`g069`/`g070` are the cleanest):

* **9 grating lines resolved** on a regular lattice, band-normal 120°±2° (Radon projection-variance max,
  FFT agrees), spacings 29.4 → 23.6 px **monotonically decreasing** — one planar surface in perspective,
  not nine independent objects.
* **Duty (bright/hole fraction) 0.40–0.48** across 7 parallel scan lines; second-moment band width
  3.46σ ≈ 15 px against a 26.7 px period → 0.42. **k = 10 predicts 0.469. k = 2 predicts 0.094.**

**`cell.s0.x704_y384` is READERLESS, is named by NO channel except CHANNEL A, and it is on the screen.**
The container's only binder of column 704 is entry slot 1 of the multi-part record `0x2f9a4`
(re-confirmed offline: ef424 holds 11 GEOM blocks, `0x2f9bc` is the only P=2 record and the only binder
of that column), so the k=10 grating fingerprints that entry uniquely.

⚠ **What this does and does not establish.** It answers **drawn-ness**, which is the question
BINDING-IS-NOT-A-DRAW made the gate — and the ghost table's prior was hostile: **14 scenery cells carry a
census 15bpp, 6 had been probed in-game, and every one was bound-never-drawn or drawn at another depth**
(ef429 twice, ef446, ef251). ef424 (704,384) is the **first channel-A cell to come back DRAWN**.
It does **not** yet establish the DEPTH — a zero-write is depth-invariant by construction. That is cast B.

### 7.2 ★ THE ORDER RIDER READS **IDENTITY** — and cast A alone was enough

The grating is on the **BLADE (part 1)**, not the shaft. Two independent legs, and they were derived
from opposite directions before being compared:

* **From the video (geometry-free).** For a 32-unit-wide tube to show a 10-period grating, either the
  periods run along its 606-unit length — then each band is at most the tube's *width*, **26–29 px**,
  against **123–180 px measured** (5–6×) — or across its width, giving a **2.6–2.9 px** period against
  **26.7 px measured** (10×). The 260×422-unit sheet fits exactly: 10 periods × ~24 px over its 260-unit
  y-axis = 0.92 px/unit, which then *predicts* the shaft's cross-axis width at 32 × 0.92 ≈ **29 px**
  against **26–28 px measured**. The solid tapered shaft is **visibly ungrated over ~500 px**, and the
  banded sheet **straddles the shaft on its own centreline** (3 px from the 9-line stack's midpoint) —
  which is what part 1's `x ≡ 0, y ∈ [−130,130]` demands.
* **From the container (video-free).** Part 0 = a closed square-section tapered TUBE in 3 telescoping
  segments, 19:1, z −1028…−422 = the **shaft**; part 1 = a zero-thickness sheet at x ≡ 0 with a wide
  guard lobe, z −422…0 = the **blade**, tip at z=0. The two orderings' screen signatures are visually
  disjoint, and the offline render predicted them **before** the video was scored: IDENTITY → the blade
  is chopped into ~10 transverse see-through bands and the shaft carries 2 marks in its rear taper;
  REVERSED → the shaft's rear 40 % becomes a dashed line of 8–10 segments while the blade carries 1–2.
  **The screen shows the first.**

**part 1 → entry slot 1 → column 704 ⇒ the array is read in FILE ORDER (identity).** Confidence ~0.90.

⚠ **AND IT MOVES NO CONSTANT.** `ORDER_UNMEASURED` stands exactly as shipped; `w6b3i_gates` I8 (THE ORDER
CLAUSE IS NOT SHIPPED) still passes and must keep passing. This is **one observation on one container**,
and it is written here rather than promoted. Promotion needs its own evidence bar and its own gated
decision — §8.3's condition (i) is *the order MEASURED*, and a single-vehicle screen read is not that.

### 7.3 What the geometry slice killed, and what it opened

* **KILLED — the UV shortcut.** The hoped-for discriminator (*"one part barely reaches the lower cell, so
  it cannot show the stripes"*) is **falsified**: part 0 touches v≥128 on 16/32 faces (38.2 % of its 3D
  area), part 1 on 64/68 (73.0 %), and **all 10 stripes land on covered rows for BOTH parts**. Geometry
  alone can never settle the order — that *is* the unmeasured clause.
* **OPENED — the second array.** `rec+0x10`'s unread second array reads `(0x0080, 0x0000)` /
  `(0x0000, 0x0000)`, and **0x0080 = 128** is a suspiciously v-offset-shaped number on a page whose
  addressable split is exactly v=128. If that array is a per-slot V-offset, cell attribution shifts and
  these ladder cells were struck on the right rows for the wrong reason. `W6b3-ARCHIVE.md` §1.1 scored
  that array as an in-record null (0/309, 0/264) on the *tpage/clut* predicate — which does not test a
  v-offset reading. **Named here, unexamined, and it is the cheapest open lead this rung produced.**
* Also recorded: **two javelin instances** are on screen in g059–g064 (two congruent gratings 66° apart,
  each with its own solid shaft) — the record is drawn more than once per cast, consistent with W6b-1's
  *scenery texel art is TEXTURE art, not placard art*.
* The **k=2 mark was NOT positively located** (confidence ~0.35): one longitudinal see-through slit on the
  shaft sits at a constant fractional width, but at 2.7× the predicted stripe width and with no second
  slit. It is also **not diagnostic** — 7 other records bind column 448, so a 2-band artifact anywhere is
  uninformative. Nothing rests on it.

### 7.4 Resting state at the end of cast A / start of cast B

Probe **REVERTED** (`revert_probe.py` → `deleted …\SpecialEffects\ef424`, install back to ABSENT/stock),
**then** the ink cast deployed — the ledger trap avoided in the order §2 requires. The kit's plan records
`existed: None / backup: None` for the install path, so its revert **deletes to stock**. Live now:
`…\FF9CustomMap\FF9_Data\SpecialEffects\ef424` = **`69ed527d…`**, the cast-B container. ef211's pool
wheel untouched (`cbcc9fde…`, mtime unmoved). A 75 MB `sfxmeshprobe.log` that had never been archived was
copied to `…\repaint-w6b\capture-logs\sfxmeshprobe.pre-odin-cast.2026-07-28.log` before the cast could
overwrite it. **Cast B needs no relaunch — recast and read §4.**

---

## 8. ★★ CAST B WAS CAST, AND REFUTED — CAST C IS THE DEPTH DISCRIMINATOR

### 8.1 What cast B bought, and what it did not

Cast B deployed (container `69ed527d…`, **live on the install now**) and the owner's video was scored
twice — a quantitative census, then an adversarial refutation. **Two results stand and must keep their
credit:**

* **the cell is DRAWN and the surface is `cell.s0.x704_y384`.** Cast A gave **10 cycles** and cast B
  **5 cycles** on the *same pixels* over an identical 282 px span — a threshold-free 2:1 that no stock
  feature can produce, because a stock feature cannot change its spatial frequency between two casts.
  Confidence 0.98.
* **BLADE (GEOM part 1) → slot 1 → column 704, IDENTITY ordering.** It rests on the band COUNT and is
  therefore **depth-invariant**, so it survives however the depth resolves. Confidence 0.96.
  (`ORDER_UNMEASURED` still stands — written in the study, promoted nowhere.)

**And the depth verdict does NOT rest on the ink.** Every one of cast B's three verdict rows is void:

| cast B's key | why it is void |
|---|---|
| clean bands → 8bpp | at 4bpp the ink byte `0xFF` is nibbles **(15, 15) — two IDENTICAL texels**, so a 4bpp read renders the bands **perfectly solid** too |
| pin-striped → 4bpp | same reason. There is nothing to pin-stripe |
| one solid wrong hue → 15bpp | **87.4 %** of the ink's 15bpp words are `0xFFFF` = pure **white**, at the **same rows** |

Band COUNT, ROW POSITION and SOLIDITY are **depth-invariant by construction** — the stamp writes whole
byte ROWS, and a byte row is a texel row at 4, 8 and 15 bpp alike. What actually carried the verdict to
0.87 was **the surrounding STOCK art** (99.9 % red-family, which neither a 4bpp/CLUT-0 read at 28.3 %
blue nor a 15bpp read at 29 % green can produce) — an argument that **needs no ink at all** and was
available from cast A. Also withdrawn: the "±2 % tangent pitch across five bands" claim (a narrow-strip
artifact; the real spread is 3×) and the frame-diff CONTAINMENT claim (containment rests on the byte
ledger, not on the diff). The ink's palette identity is **undecidable** on cast B — it clipped.

### 8.2 The fix: the same five bands, ink byte `0xF0`

**Spec `odin_channel_a_c.toml`. One variable moves: the ink byte.** The three depths then give three
mutually exclusive, unmistakable outcomes — every number re-derived from the user's own container:

| depth | `0xF0` renders as |
|---|---|
| **8bpp** | index 240 = **rgb(222,115,115) SALMON**, luma 147 (Rec.601) — well below saturation, so its hue survives additive blending. Calibrated on cast B's own clip statistics (gain ≈ 0.86) it reads **(231,139,139) at backdrop 40 → (255,169,169) at backdrop 70**, G/R ≈ 0.60; the refutation's "~(255,170,170)" is the bright end of that range |
| **4bpp** (natural CLUT base) | nibbles (0, 15) → **TRANSPARENT alternating with rgb(24,0,8)** — a 50 %-duty 1-texel **transparent comb** in the band. ⚠ **But the screen read is not "the blade thins"** — at 4bpp the *whole cell* is 17.9 % opaque at mean luma 11, a dark shredded smear with **no recognisable spearhead at all**. See §8.3 |
| **15bpp** | word `0xF0F0` → **rgb(131,57,230) VIOLET-BLUE** — and only 0.1 % of the javelin body is blue, so it is unmissable |

**THE COUNT STAYS FIVE** so the cell identity stays self-verifying (10 : 5 is the 2:1). **Row 2 (the 448
order cell) is byte-for-byte cast B's** — so cast C minus cast B is exactly **2,311 bytes, one cell,
`0xFF`→`0xF0`, nothing else**. `0xF0` is not even available on 448: index 240 is transparent under
`pal.s0.x0_y242.e256` and the stamp refuses it by name.

### 8.3 ★ READ THE OFFLINE PREDICTION BEFORE THE VIDEO

`predict_cast_c.py` renders the **actual patched bytes** four ways into
`…\ef424-channel-a\predict-c\` — 8bpp, 4bpp/CLUT-0, 4bpp/base-240 window, 15bpp — plus a
`…SHEET.png` that shows each as texture, v-flipped (screen order), and composited **additively over
rgb(55,55,55)**, which is what the engine does. Measured on the panels:

| read | opaque | mean luma | red / green / blue | looks like |
|---|---|---|---|---|
| **8bpp** | 26.4 % | 97 | 88 / 0 / 5 % | the ornate maroon spearhead with **5 salmon bars** |
| **4bpp CLUT-0** | 17.9 % | **11** | 54 / 0 / 6 % | destroyed art, **no bright content anywhere** |
| 4bpp base-240 | **100 %** | 158 | 100 / 0 / 0 % | a **solid opaque pink slab** — no cutout, no cave through it |
| **15bpp** | 28.3 % | 99 | 23 / 17 / **60 %** | half-width **violet** confetti |

The three primary hypotheses are unmistakable. **The one honest overlap:** the contrived base-240 window
shares the pink HUE with 8bpp — it is separated primarily by the **CUTOUT**, not by colour (100 % opaque
vs 26.4 %), and secondarily by about **20 DN of Cr and 38 DN of Y** once both are put through the blend
model. So the read is *"salmon bands **and** the cave still visible through the head's gaps"*, and a head
that turns into a solid opaque rectangle is the base-240 residue, not a verdict. (That residue is in any
case independently dead: **cast A punched 10 transparent slots through this cell and they were counted on
screen**, which a 100 %-opaque base-240 read could not have shown.) Compare the video to the sheet; never
to a memory of the table.

⚠ **What cast C actually buys.** The 4bpp and 15bpp rows corroborate but add little — casts A and B
already showed a coherent ornate spearhead, which neither depth can produce. **The new content is the
POSITIVE 8bpp row**: an ink-borne measurement of the draw depth *and* of the ink's palette identity,
where cast B's depth verdict rested entirely on the surrounding stock art. Read the salmon; the other two
rows are there so a surprise has somewhere to land.

### 8.4 The sequence — and ⚠ THE REVERT IS NOT CAST B'S

```
  0.  (bench rows 203/204 already registered; ef424 overrides are HOT -- NO relaunch)
  1.  regen   cd studies\custom-summons\tier-w
              py odin_band_stamp.py --cast c
              (cwd = ff9mapkit\)
              py -m ff9mapkit summon-reskin build  ../studies/custom-summons/tier-w/odin_channel_a_c.toml ^
                 --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\stage-c
              py predict_cast_c.py
  2.  deploy  py -m ff9mapkit summon-reskin deploy ../studies/custom-summons/tier-w/odin_channel_a_c.toml ^
                 --out C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\stage-c
  3.  RECAST  (no relaunch -- a page upload is itself the cache-invalidating event).  Video, not stills.
  4.  READ    section 8.2's table against section 8.3's sheet.  Archive the [SfxProbe] log to capture-logs\.
  5.  revert  see below
```

**`--out stage-c` IS LOAD-BEARING.** `stage/` holds **cast B's** first-deploy snapshot and its
`revert_summon_repaint_ledger_424.py`, which records `backup: null` — i.e. *delete to stock*. That
snapshot is taken **once per root and never overwritten**, so building cast C into `stage/` would make
cast C ride cast B's ledger. Its own root gets its own honest ledger.

⚠ **AND THAT LEDGER SAYS SOMETHING DIFFERENT.** Rehearsed against a temp mod folder primed with cast B:
the cast-C deploy snapshots the live override — which at that moment is **cast B (`69ed527d…`)**, not
ABSENT — into `stage-c\backups\ef424.pre-<stamp>`, so **`revert` from `stage-c` RESTORES CAST B, it does
not delete.** Verified idempotent (run twice → `69ed527d…` both times). **Getting back to stock is TWO
steps, in this order:**

```
  py -m ff9mapkit summon-reskin revert ../studies/custom-summons/tier-w/odin_channel_a_c.toml ^
     --out ...\ef424-channel-a\stage-c     -> restores CAST B (69ed527d...)
  py -m ff9mapkit summon-reskin revert ../studies/custom-summons/tier-w/odin_channel_a.toml ^
     --out ...\ef424-channel-a\stage       -> DELETES the override; resting state stock
```

Section 6's warnings still apply in full: **name the spec, never `--ef 424`** (that routes to the
CLUT/reskin lane's root), **pass the same `--out` the deploy used**, and **never `--dry-run` into the
default root**.

### 8.5 What is staged for cast C

| artifact | path |
|---|---|
| generator (extended: `--cast`, `--ink-byte`, `--emit-spec-guards`) | `studies/custom-summons/tier-w/odin_band_stamp.py` |
| cast C spec | `studies/custom-summons/tier-w/odin_channel_a_c.toml` |
| prediction renderer | `studies/custom-summons/tier-w/predict_cast_c.py` |
| cast C figure (manifest-free, on purpose) | `…\art-channel-a\cell.s0.x704_y384.verdictbands.inkf0.png` |
| order figure — **byte-identical to cast B** | `…\art\cell.s0.x448_y384.orderbands.png` (sha `70f3c096…`) |
| staged container | `…\ef424-channel-a\stage-c\mod\FF9_Data\SpecialEffects\ef424` — sha **`0650b968…`** |
| prediction sheet + 4 panels | `…\ef424-channel-a\predict-c\` |

**Byte proof.** changed-vs-stock = **6,249 bytes**, and the offset-and-value set is **exactly** the
authored band set (0 extra, 0 missing, 0 wrong-value); 6,253 texels are authored and 4 were *already*
`0xF0` in the stock art, which is why the count is 6,249 and not 6,253. Cast C vs cast B = **2,311
bytes, all `0xFF`→`0xF0`, all inside the 704 cell, 0 in the 448 cell, 0 anywhere else.**
Regression: re-running `odin_band_stamp.py` with no arguments reproduces cast B's three artifacts
byte-identically and rebuilds to `69ed527d…` — the container live on the install.

**Refusal rungs re-driven on the new spec** (all three fire, first line quoted in the session record):
no ack → `DEPTH-UNKNOWN … ** AND THE CONTAINER STATES A DEPTH ELSEWHERE (CHANNEL A, DISCLOSE)`;
ack without `expect_bpp` → `says \`acknowledge_array_derived_depth = true\` but states NO \`expect_bpp\``;
`expect_bpp = 4` → `the spec guards 4bpp, the container's own \`so\` record's BINDING ARRAY … derives 8bpp`.
