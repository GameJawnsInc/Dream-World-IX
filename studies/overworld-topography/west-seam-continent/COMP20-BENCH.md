# comp20 on the continent — bench round (registered)

Registered 2026-10-06 BEFORE any bench write or dry run. Owner: "yes, set up the comp20 bench round."
Follows [`UAHO-JULY-STRETCHES.md`](UAHO-JULY-STRETCHES.md) and its rule: **flag RAISED FOREST contacts;
everything else carries on a flat lawn with today's `world-mountain`.**

## Why comp20, and what this round can and cannot test

- **comp20** is `(12,16)-(12,17)`: 178 tris, r_rim 31.5u, no aperture, no forest contact.
- **Its rim contacts:** 68% grass, 32% coastal rock, all at or below its seat (`context_screen`: SAFE 68% +
  SAFE-SEAT 32%, 0% raised). Buried coastal rock now has a verdict (Uaho, July).
- **It has passed once already:** July 19, on an r48 seed-42 bench at (448, −1216), rot 180°, "looks good",
  a first-deploy pass. The census noted its "coastal-lip fringe footing".

**This round CAN show** that the continent hosts a mountain that reads right, built with no authored foot
at all beyond `world-mountain`'s own zip annulus.

**It CANNOT discriminate the forest rule further.** comp20 has no forest, so it would pass under either
hypothesis. Said now so a pass isn't over-read.

## What gets built (on a scratch mirror of the live `FF9CustomMap-world`; nothing live)

1. **THE R4 REVERT,** exactly as the isle round:
   - restore `r4-pre.20260828-103332` (560 files);
   - delete the 54 R4-created ensemble parts;
   - verify byte-identity.
2. **THE CARVE:** the plan's own recorded R5 alternative line, unchanged:
   `world-mountain --mod-folder <BENCH> --near 1476,-376 --donor 12,16-17 --reach 44`.
   Dry run first, then the bench write.
3. **THE R3 RE-STAMP:** `stamp_area_policy.py` on the bench (`FF9MK_WM` / `FF9MK_BACKUP` seams), so the
   new zip/apron tris join the safe road.

**Declared, the only permitted adjustment:** if the scan refuses at `--near 1476,-376` (seam window or
clearance), retry at the R4 slot `--near 1452,-468` with the same reach. Any other refusal stops the round.

## Registered predictions

- **C1, the carve is clean.** Every `world-mountain` gate passes. The R3 re-stamp's probes pass.
- **C2, the screen on the PLACED rim** (bench lawn as the datum, the sector map's method):
  - 0% raised forest;
  - ≥ 95% of rim length at or below +0.75u over the lawn;
  - no stretch needs a foot course, a pull, a conform or an apron cap.
- **C3, only the intended files change.** Versus the live folder, the bench differs ONLY in the R4 revert
  set, the carve's span blocks (+ Disc4 mirrors), and the stamp's area bits.
- **C4, scored only after the owner's in-game look, which needs a live deploy on the owner's go:** no
  complaint about the base or the grass–mountain transition anywhere around comp20.

## Where the owner's eye will most likely land (named now)

1. **The coastal-lip fringe band** at the buried coastal-rock stretches (32% of the rim). It is comp20's
   own home footing, a coast vocabulary standing on an inland lawn: the one context class carried here with
   only Uaho's single verdict behind it.
2. **The zip annulus:** the only minted surface.
3. **comp20's scale:** peak ~21.8u against the continent, after twelve rounds on a 30u horseshoe. That's a
   design call, not a defect.

## Out of scope

- the live deploy (owner go);
- the harness rim walk (re-derived for comp20 once the look passes);
- R5's second massif;
- the horseshoe.

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 on `scratchpad/bench-comp20` (a fresh mirror of live). Nothing live was written.

### The registered score (C1–C3; C4 waits for the owner's look)

| | measured | verdict |
|---|---|---|
| **R4 revert** | bench vs `r4-pre`: 0 diffs in 560; 0 of the 54 created parts remain | **exact** |
| **C1** the carve is clean | the plan's line, unchanged, no fallback needed. Placement rot 90° at **(1486, −386)**, clearance 61.3u. Rigid rim heights 2.94–3.65 vs ground 3.20. Apron lift max 0.39u. Zip 82 tris (rise 0.51, ny ≥ 0.97, 0/82 below envelope). down 0, near-miss 0, rock rigidity 0.6%, apron slope 1.6°, atlas 0, census MISS 0. The R3 re-stamp: 1,050 verts, 52 files | **HOLDS** |
| **C2** the placed rim | the sector-map instrument re-aimed (`comp20_placed_screen.py`) calibrates exactly: rot 90°, DY +0.3644, 106/106 carried rock verts rigid on the bench mesh. Rim E over the lawn: p10 −0.14, p50 0.00, p90 +0.20; **100% ≤ +0.75**; contacts grass 96.2u + buried coastal rock 44.6u; **0% forest**, 0% high approach. No foot course, pull, conform or cap was needed or used | **HOLDS** |
| **C3** only the intended files change | `bench_vs_live.py`: 92 differing paths, all in the R4 revert set or comp20's 4 span blocks (22-23 × 5-6); **0 outside**. The "added" files are the carve's own `.bak` parkings. The col-23 x = 1536 seam weld is byte-identical on rows 5 and 6 | **HOLDS** |

**Recorded, not a gate:** with an ABSOLUTE `--mod-folder` (a bench path), `discmirror.auto_mirror` cannot
derive the game root and silently returns. So the bench's Disc4 was NOT mirrored. A live deploy names the
folder (`FF9CustomMap-world`) and mirrors as takes 9 and 12 did; check the mirror on that deploy.

**The renders** (`world-render --around 1486,-386`; atlas pixels, so they stay in the scratchpad): the rock
meets the lawn all round on its own grass-fringed foot, with no visible ramp or knoll. The horseshoe is gone
(the revert).

### For the owner's look (C4), after a live deploy on the owner's go

- **Teleport:** (1519.8, −389.3) on lawn, 34u east of the massif. Face WEST (bearing ~174°). That puts
  comp20's buried coastal-rock stretches, named target #1, straight ahead.
- **The deploy itself:** the R4 revert, then the carve line with `--mod-folder FF9CustomMap-world`, then
  `stamp_area_policy.py`, all with backups first. The bench measured all of it.

### DEPLOYED LIVE (2026-10-06, owner: "yes, deploy comp20 live")

- **Preflight:**
  - live's R4 blocks = the take-12 bench (55/55);
  - live unchanged since the bench (the same 92 expected diffs, 0 outside);
  - FF9.exe not running.
- **Backup:** the whole live WorldMap Disc1/0_1 + Disc4/0_1 tree → `backups/west-seam-continent/comp20-pre.20261006-193908`
  (1,737 files, 0 mismatches). **THE REVERT.** Restore only the continent's blocks from it: it also holds other
  sessions' content as of 19:39.
- **The R4 revert live:**
  - restored 560 files from `r4-pre`;
  - removed the 54 R4-created ensemble parts, each confirmed present in the backup first;
  - 0 diffs, 0 left.
- **The carve live:** `world-mountain --mod-folder FF9CustomMap-world --near 1476,-376 --donor 12,16-17 --reach 44`.
  Identical to the bench: rot 90° at (1486, −386), clearance 61.3u, every gate the same. **Disc4 auto-mirror ran**
  (36 files: the folder was named).
- **The re-stamp live:** run from the MAIN repo copy, so its backup lands there:
  - 2,100 verts across 52 files (both discs);
  - backup `r3-pre-area14.20261006-194031`;
  - `probe_area14.py` ALL CHECKS PASS (a–e).
- **Verification:**
  - live Disc1 = the measured bench Disc1 (727 identical, 0 differing; `.bak` parkings excluded);
  - Disc4 Terrain = Disc1 on all 4 span blocks.

**For the owner's look (C4):**
- teleport **(1519.8, −389.3)** and face WEST (~174°); the coastal-rock stretches are straight ahead;
- walk the base all round;
- the harness's `rimwalk_take8.py` stations are for the horseshoe and are now STALE (re-derive for comp20
  after the look).
