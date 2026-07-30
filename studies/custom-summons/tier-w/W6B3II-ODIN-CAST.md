# W6b-3 (ii) — THE ODIN CHANNEL-A CAST LADDER. ef424 `Odin__Short`, bench rows 203/204

> **Nothing in this ladder has been deployed.** Every artifact below is STAGED: the bench build ran
> offline into `rung8-epic/stage/final/`, the probe and the ink cast into
> `C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\`. No install write, no `Memoria.ini` edit,
> no relaunch, no commit. This file is the sequence a session runs when the owner is at the machine.

**WHAT IS BEING MEASURED.** `cell.s0.x704_y384` is bound by exactly one thing in the container: entry
slot 1 of the multi-part `so` record 0x2f9a4 (P = 2). `page_depth_view` is ABSENT for that whole column,
so **CHANNEL A is the only channel that states its 8 bpp** — and channel A has never put a texel on
screen (0 hits / 4 misses / 2 vacuous passes over six named cells). Two questions, in this order:

| | question | instrument | answer shape |
|---|---|---|---|
| **CAST A** | is the cell DRAWN at all? | `odin_cell_probe.py` — zero stripes, 10 on the verdict cell, 2 on the order cell | banding / clean |
| **CAST B** | is channel A's 8 bpp the DRAW depth? | `odin_channel_a.toml` — 5 ink bands on the verdict cell, 3 on the order cell | clean / pin-striped / wrong-hue |
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
